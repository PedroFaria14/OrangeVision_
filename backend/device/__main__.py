import argparse
import getpass
import json
import time
from contextlib import ExitStack
from uuid import UUID, uuid4

from .api import ApiFailure, DeviceApi, Offline
from .config import DeviceSettings
from .detector import ModelFailure
from .locking import device_lock
from .storage import Store
from .sync import Synchronizer
from .worker import ClockFailure, PairingFailure, Worker


def main():
    parser = argparse.ArgumentParser(
        description='OrangeVision no equipamento — execução local autorizada.'
    )
    parser.add_argument(
        'command',
        choices=(
            'pair',
            'cancel-pairing',
            'capture',
            'run',
            'close',
            'sync',
            'status',
            'job',
            'samples',
        ),
    )
    parser.add_argument(
        '--request-id',
        type=UUID,
        help='ID estável para repetir a consulta de um comando, sem duplicar captura.',
    )
    parser.add_argument(
        '--loop',
        action='store_true',
        help='Executar sync ou samples continuamente, sem controlar a câmera.',
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Recupera a tentativa de pair salva localmente, sem redigitar o código.',
    )
    sample_settings = parser.add_mutually_exclusive_group()
    sample_settings.add_argument(
        '--draft', help='Rascunho HSV para amostras, sem habilitar categorias.'
    )
    parser.add_argument('--ai', action='store_true', help='Usar detector ONNX local para amostras.')
    sample_settings.add_argument(
        '--calibration', help='Calibração validada para amostras experimentais.'
    )
    args = parser.parse_args()
    if args.resume and args.command != 'pair':
        parser.error('--resume só pode ser usado com pair.')
    if (args.draft or args.calibration) and args.command != 'samples':
        parser.error('--draft e --calibration são opções do comando samples.')
    if args.ai and args.command != 'samples':
        parser.error('--ai é uma opção do comando samples.')
    api, camera = None, None
    try:
        settings = DeviceSettings.load()
        api = DeviceApi(settings)
        if args.command == 'samples':
            from .samples import run_samples

            camera_store = Store(settings.database)
            camera_store.initialize()
            run_samples(
                api,
                draft=args.draft,
                calibration=args.calibration,
                loop=args.loop,
                ai=args.ai,
                camera_store=camera_store,
            )
            return
        store = Store(settings.database)
        store.initialize()
        if args.command == 'job':
            if not args.request_id:
                raise RuntimeError('Informe --request-id para consultar um comando existente.')
            print(json.dumps(store.job(str(args.request_id)), ensure_ascii=False))
            return
        if args.command == 'status':
            grant = store.active_grant()
            print(
                json.dumps(
                    {
                        'session_id': grant['id'] if grant else None,
                        'operator_name': grant['operator_name'] if grant else None,
                        'state': grant.get('state') if grant else None,
                        'authorization_expires_at': grant.get('authorization_expires_at')
                        if grant
                        else None,
                        'pairing_pending': store.pairing_attempt() is not None,
                        'outbox': store.counts(),
                        'camera_outbox': store.camera_sample_counts(),
                    },
                    ensure_ascii=False,
                )
            )
            return
        if args.command == 'sync':
            sync = Synchronizer(store, api)
            while True:
                print(f'Confirmados nesta execução: {sync.once()}; outbox: {store.counts()}')
                if not args.loop:
                    break
                time.sleep(5)
            return
        with device_lock(settings.lock_path), ExitStack() as resources:
            store.recover_interrupted()
            worker = Worker(settings.device_id, store, api)
            if args.command == 'pair':
                print(
                    worker.pair(
                        None
                        if args.resume
                        else getpass.getpass('Código de pareamento (não será exibido): ')
                    )
                )
                return
            if args.command == 'cancel-pairing':
                worker.cancel_pairing()
                print('Tentativa local reconciliada; nenhum novo comando de captura foi enviado.')
                return
            if args.command == 'close':
                worker.close_inspection()
                print('Encerramento confirmado ou nenhuma sessão local ativa.')
                return
            from .camera import Camera
            from .vision import CalibratedVision

            vision = CalibratedVision.load(settings.calibration_path)
            camera = Camera(settings)
            resources.callback(camera.close)
            worker.camera, worker.vision = camera, vision
            if args.command == 'capture':
                request_id = str(args.request_id or uuid4())
                print(f'Comando: {request_id}')
                print(f'Análise persistida localmente: {worker.capture(request_id)}')
            else:
                while True:
                    grant = store.active_grant()
                    name = grant['operator_name'] if grant else 'nenhum'
                    print(
                        'Operador: '
                        + ''.join(character for character in name if character.isprintable())
                    )
                    command = (
                        input(
                            '[p] parear | [c] capturar | [e] encerrar sessão | [s] sair do executor: '
                        )
                        .strip()
                        .lower()
                    )
                    if command == 's':
                        break
                    if command == 'e':
                        worker.close_inspection()
                        camera.close()
                    elif command == 'p':
                        print(worker.pair(getpass.getpass('Código de pareamento: ')))
                        camera.close()
                    elif command == 'c':
                        request_id = str(uuid4())
                        print(f'Comando: {request_id}')
                        try:
                            print(f'Análise persistida localmente: {worker.capture(request_id)}')
                        except Exception as exc:
                            print(
                                f'Captura não confirmada; tipo={type(exc).__name__}. Consulte o comando antes de repetir.'
                            )
    except KeyboardInterrupt:
        print('Executor interrompido; pendências locais preservadas.')
    except (ClockFailure, PairingFailure, ModelFailure) as exc:
        print(str(exc))
        raise SystemExit(1) from None
    except Offline:
        print(
            'Sem comunicação com a API. O estado local foi preservado. Para pareamento pendente, restabeleça a rede e use pair --resume.'
        )
        raise SystemExit(1) from None
    except ApiFailure as exc:
        guidance = {
            401: 'A credencial do equipamento não foi aceita. Confira o provisionamento, sem compartilhar a credencial.',
            403: 'Operação não autorizada. Confira o vínculo do equipamento e a autorização da sessão.',
            404: 'Código ou sessão não encontrado. Confira a inspeção no site.',
            409: 'Conflito de estado. Confira a sessão no site; tente pair --resume se houve resposta perdida.',
            410: 'Autorização ou código expirado. Reconcilie a tentativa anterior antes de iniciar outra inspeção.',
            422: 'Dados da operação inválidos. Confira o código temporário e a configuração do equipamento.',
            429: 'Limite de tentativas atingido. Aguarde antes de repetir.',
        }.get(
            exc.status,
            'Falha de comunicação com a API. Preserve a tentativa local e tente novamente após verificar o servidor.',
        )
        print(f'Operação recusada pela API (HTTP {exc.status}). {guidance}')
        raise SystemExit(1) from None
    except Exception as exc:
        print(
            f'Operação não concluída; tipo={type(exc).__name__}. Verifique configuração, autorização e diagnóstico local.'
        )
        raise SystemExit(1) from None
    finally:
        if camera:
            camera.close()
        if api:
            api.close()


if __name__ == '__main__':
    main()
