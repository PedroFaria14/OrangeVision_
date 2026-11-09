"""Janela de captura: detecção, revisão da foto e rede com estados independentes."""

import time
from datetime import UTC, datetime
from queue import Empty, SimpleQueue
from uuid import uuid4

from .camera_dashboard import DashboardStatus, action_at, failure_notice, render_frame
from .camera_review import CameraReview, CaptureNotAuthorized, confirm_photo, connect_session
from .detector import MODEL_NAME, ModelFailure
from .framing import safe_framing_hint
from .live_detection import LiveDetection
from .sample_evaluations import poll_sample_evaluation
from .samples import flush_camera_samples, process_one
from .worker import ClockFailure, PairingFailure

WINDOW = 'OrangeVision - captura integrada'
EMPTY_DETECTION = {'status': 'not_detected', 'box': None, 'count': 0, 'inference_ms': 0.0}
FRAMING_SECONDS = 0.3


def error_message(error):
    if isinstance(error, (ClockFailure, ModelFailure, CaptureNotAuthorized, PairingFailure)):
        return str(error)
    return failure_notice(error)


_last_audit = {}


def audit(stage, error=None, detail=None):
    """Registro no terminal por etapa; repete só quando a situação muda (sem segredos)."""
    if error is None:
        line = detail
    else:
        line = f'ERRO {type(error).__name__}: {str(error)[:200] or "-"}'
    if line and _last_audit.get(stage) != line:
        print(f'[{datetime.now():%H:%M:%S}] {stage}: {line}', flush=True)
    _last_audit[stage] = line


SESSION_CHECK_SECONDS = 15
_last_session_check = {'at': -float('inf')}


def observe_session(store, worker, now=None):
    """Confirma sozinho um encerramento pedido no site, sem esperar a próxima captura.

    Usa a mesma verificação da captura: se o site pediu encerramento, o equipamento
    confirma, desativa a autorização local e passa a pedir novo pareamento [P].
    """
    now = time.monotonic() if now is None else now
    if worker is None or now - _last_session_check['at'] < SESSION_CHECK_SECONDS:
        return None
    _last_session_check['at'] = now
    grant = store.active_grant()
    if not grant:
        return None
    try:
        worker._capture_grant(grant)
    except RuntimeError as error:
        if 'encerrada' in str(error):
            audit('sessao', detail='Encerramento pedido no site foi confirmado. Pareie de novo com [P].')
            return 'closed'
        audit('sessao', error)
        return 'error'
    except Exception as error:
        audit('sessao', error)
        return 'error'
    audit('sessao', detail='ativa')
    return 'active'


def maintain_camera(store, api, detector, calibration, publish, worker=None):
    """Cada fase informa seu estado; falha no heartbeat não impede tentar o upload."""
    try:
        api.heartbeat_samples('ready', MODEL_NAME, 'Camera integrada e fila com IA.')
    except Exception as error:
        audit('conexao', error)
        publish({'kind': 'connection_error', 'error': error})
    else:
        publish({'kind': 'connected'})
    observe_session(store, worker)
    try:
        flush_camera_samples(store, api, on_event=publish)
    except Exception as error:
        audit('envio', error)
        publish({'kind': 'upload_error', 'error': error})
    processing_id = None

    def processing_event(event):
        nonlocal processing_id
        if event['kind'] == 'processing':
            processing_id = event['sample_id']
        publish(event)

    try:
        processed = process_one(
            api, calibration, validated=calibration is not None,
            detector=detector, on_event=processing_event, store=store,
        )
        audit('fila', detail=(
            f'amostra {processed["id"][:8]} -> {processed["state"]}' if processed else 'sem amostras pendentes'
        ))
    except Exception as error:
        audit('fila' if not processing_id else f'analise {processing_id[:8]}', error)
        publish({
            'kind': 'analysis_error' if processing_id else 'connection_error',
            'sample_id': processing_id, 'error': error,
        })
    try:
        poll_sample_evaluation(store, api)
    except Exception as error:
        audit('gemini', error)
        publish({'kind': 'connection_error', 'error': error})


def run_window(
    camera, detector, worker, api, pool, gate, automatic, headless, calibration, save_automatic
):
    import cv2

    review = CameraReview(worker.store, restore=not headless)
    # Com localização por cor, a captura manual [C] não depende do detector COCO,
    # que confunde laranja verde com maçã e laranja manchada com outros objetos.
    color_fallback = bool(calibration and calibration.get('color_fallback') is True)
    print(
        f'Calibracao: {calibration["version"]} (localizacao por cor: {"sim" if color_fallback else "nao"})'
        if calibration else 'Calibracao: NENHUMA carregada (confira CALIBRATION_PATH).',
        flush=True,
    )
    dashboard = DashboardStatus()
    if calibration is None:
        dashboard.analysis_detail = 'Sem calibracao validada carregada. Use --calibration com arquivo validado.'
    dashboard.restore(worker.store)
    details = False
    details_page = 0
    events = SimpleQueue()
    capture_future = maintenance_future = None
    capture_kind = None
    requested_sequence = None
    request_started = 0
    capture_notice = (
        'Foto anterior recuperada. Use ou tire outra.' if review.photo else
        'Posicione a laranja. C captura; U confirma o envio.'
    )
    connection_notice = 'Aguardando contato com o servidor.'
    last_poll = last_refresh = -float('inf')
    observed_sequence = 0
    detection_error = None
    clicks = []
    live = LiveDetection(detector)
    # Dica de enquadramento: no vídeo ao vivo a cada FRAMING_SECONDS; na revisão,
    # uma vez por foto guardada. Só orienta; a análise continua com suas recusas.
    framing, framing_at, framing_photo = None, -float('inf'), None

    if not headless:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW, 960, 720)

        def mouse(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONUP:
                action = action_at(x, y, review.photo is not None)
                if action:
                    clicks.append(action)

        cv2.setMouseCallback(WINDOW, mouse)
    print('C: capturar | U/Enter: usar foto | R: tirar outra | P: sessao | I: detalhes | A: modo | Q: sair.')
    print('Dica: fundo branco/cinza liso, luz de frente ou de cima e a fruta no centro (~1/3 da imagem).')
    print('Detectar a fruta nao comprova qualidade. O envio exige confirmacao do servidor.')
    live.start()
    try:
        while True:
            while True:
                try:
                    event = events.get_nowait()
                except Empty:
                    break
                dashboard.handle(event)
                kind = event['kind']
                if kind in ('connected', 'synced', 'result'):
                    connection_notice = 'Servidor respondeu as ' + datetime.now().strftime('%H:%M:%S')
                elif kind in ('connection_error', 'upload_error', 'analysis_error'):
                    connection_notice = failure_notice(event['error'])
                last_refresh = -float('inf')

            if capture_future is not None and capture_future.done():
                try:
                    capture_notice = capture_future.result()
                    if capture_kind == 'review':
                        review.submitted()
                        live.reset()
                    elif capture_kind == 'connect':
                        review.sending = False
                    if capture_kind != 'connect':
                        gate.captured()
                        dashboard.upload = 'Na fila para envio. Foto salva neste equipamento.'
                        dashboard.upload_tone = 'orange'
                    last_poll = last_refresh = -float('inf')
                except Exception as error:
                    capture_notice = error_message(error)
                    review.sending = False
                    if capture_kind != 'connect':
                        dashboard.upload = 'Confirmacao falhou. Foto preservada: ' + capture_notice
                        dashboard.upload_tone = 'red'
                    if capture_kind == 'automatic':
                        automatic = False
                print(capture_notice)
                capture_future = None
            if maintenance_future is not None and maintenance_future.done():
                try:
                    maintenance_future.result()
                except Exception as error:
                    connection_notice = error_message(error)
                maintenance_future = None
                if (
                    not headless and review.photo is None and capture_future is None
                    and worker.store.camera_sample_counts().get('quarantined', 0)
                ):
                    recovered = CameraReview(worker.store)
                    if recovered.photo:
                        review = recovered
                        requested_sequence = None
                        live.reset()
                        capture_notice = 'Envio retido. Foto recuperada: P verifica sessao; U confirma.'

            now = time.monotonic()
            if now - last_refresh >= 1:
                dashboard.refresh(worker.store, getattr(worker, 'device_id', None))
                last_refresh = now
                if dashboard.counts.get('pending') and dashboard.upload_tone == 'muted':
                    dashboard.upload = 'Fotos salvas aguardando envio.'
                    dashboard.upload_tone = 'orange'

            ready = False
            snapshot = None
            if review.photo:
                frame, detection = review.photo.frame, review.photo.detection
            else:
                frame = camera.capture()
                sequence = live.submit(frame, datetime.now(UTC).isoformat(), time.monotonic())
                snapshot, error = live.latest()
                if error is not None and error is not detection_error:
                    capture_notice = 'Falha na IA: ' + error_message(error)
                    print(capture_notice)
                detection_error = error
                if snapshot is not None and snapshot.fresh(time.monotonic()):
                    detection = snapshot.detection
                    if snapshot.sequence != observed_sequence:
                        observed_sequence = snapshot.sequence
                        ready = gate.observe(detection, snapshot.captured_monotonic)
                else:
                    snapshot = None
                    detection = EMPTY_DETECTION
                    gate.observe({'status': 'unavailable'}, time.monotonic())

                # Manual capture waits for a NEW analyzed frame and saves that exact frame.
                if requested_sequence is not None:
                    if snapshot is not None and snapshot.sequence >= requested_sequence:
                        try:
                            if review.take(
                                snapshot.frame, snapshot.detection, snapshot.captured_at,
                                worker.store.active_grant(),
                                allow_undetected=color_fallback,
                            ):
                                capture_notice = 'Foto guardada. Clique USAR FOTO [U] para autorizar o envio.'
                                dashboard.upload = 'Aguardando sua confirmacao em USAR FOTO [U].'
                                dashboard.upload_tone = 'orange'
                                frame, detection = review.photo.frame, review.photo.detection
                                live.reset()
                            else:
                                capture_notice = 'Nenhuma laranja unica detectada. Reposicione e pressione C.'
                        except Exception as error:
                            capture_notice = error_message(error)
                        requested_sequence = None
                        ready = False
                        print(capture_notice)
                    elif time.monotonic() - request_started > 15:
                        requested_sequence = None
                        capture_notice = 'IA sem resultado recente. Confira o erro e tente capturar novamente.'

            if not headless:
                if review.photo is not None:
                    if framing_photo is not review.photo:
                        framing = safe_framing_hint(review.photo.frame, calibration)
                        framing_photo = review.photo
                elif framing_photo is not None or time.monotonic() - framing_at >= FRAMING_SECONDS:
                    framing = safe_framing_hint(frame, calibration)
                    framing_at, framing_photo = time.monotonic(), None
                canvas = render_frame(
                    frame, detection, review.photo is not None, review.sending,
                    automatic, ready, gate.armed, capture_notice, connection_notice,
                    dashboard=dashboard, details=details, details_page=details_page,
                    framing=framing,
                )
                cv2.imshow(WINDOW, canvas)
                key = cv2.waitKey(20) & 0xFF
                try:
                    visible = cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) >= 1
                except cv2.error:
                    visible = False
                if key in (ord('q'), ord('Q')) or not visible:
                    break
            else:
                time.sleep(0.02)
                key = -1
            if 65 <= key <= 90:
                key += 32
            action = clicks.pop(0) if clicks else None
            action = {
                ord('c'): 'capture', ord('u'): 'use', 10: 'use', 13: 'use',
                ord('r'): 'retake', ord('p'): 'connect', ord('a'): 'mode',
                ord('i'): 'details',
                ord('['): 'previous_details', ord(']'): 'next_details',
            }.get(key, action)

            if action == 'details':
                details = not details
                details_page = 0
            elif details and action in ('previous_details', 'next_details'):
                details_page += -1 if action == 'previous_details' else 1
            elif action == 'mode' and not review.photo and not review.sending:
                automatic = not automatic
                requested_sequence = None
                live.reset()
                gate.observe({'status': 'unavailable'}, time.monotonic())
                capture_notice = 'Modo automatico ativado.' if automatic else 'Modo manual ativado.'
            elif action == 'connect' and not review.sending and capture_future is None:
                try:
                    from .session_dialog import ask_connection_code

                    requested_sequence = None
                    response = ask_connection_code(worker)
                    live.reset()
                    gate.observe({'status': 'unavailable'}, time.monotonic())
                    if response:
                        review.sending = True
                        capture_kind = 'connect'
                        capture_future = pool.submit(connect_session, worker, *response)
                        capture_notice = 'Conectando sessao. Foto guardada nao sera descartada.'
                    last_refresh = -float('inf')
                except Exception as error:
                    capture_notice = error_message(error)
            elif action == 'capture' and review.sending:
                capture_notice = 'Operacao em andamento. Aguarde antes de capturar.'
            elif action == 'capture' and not review.photo:
                if requested_sequence is None:
                    requested_sequence = sequence + 1
                    request_started = time.monotonic()
                capture_notice = 'Validando um novo quadro com a IA. Aguarde a foto para confirmar.'
            elif action == 'retake' and review.photo and not review.sending:
                review.retake()
                live.reset()
                gate.observe({'status': 'unavailable'}, time.monotonic())
                capture_notice = 'Mostre a laranja e capture novamente.'
                dashboard.upload = 'Foto de revisao descartada. Envios anteriores preservados.'
                dashboard.upload_tone = 'muted'
            elif action == 'use' and review.photo and not review.sending and capture_future is None:
                review.sending = True
                capture_kind = 'review'
                capture_future = pool.submit(confirm_photo, worker, review.photo)
                capture_notice = 'Foto salva. Confirmando autorizacao para enviar...'
                dashboard.upload = 'Confirmando autorizacao (ainda nao enviada).'
                dashboard.upload_tone = 'orange'
            elif (
                automatic and ready and snapshot is not None and review.photo is None
                and requested_sequence is None and capture_future is None
            ):
                grant = worker.store.active_grant()
                if not grant:
                    automatic = False
                    capture_notice = 'Automatico pausado: pareie uma sessao antes de enviar fotos.'
                else:
                    capture_kind = 'automatic'
                    capture_future = pool.submit(
                        save_automatic, worker, grant, snapshot.frame.copy(),
                        snapshot.captured_at, str(uuid4()),
                    )
                    capture_notice = 'Salvando captura automatica autorizada...'
                    dashboard.upload = 'Salvando foto localmente (ainda nao enviada).'
                    dashboard.upload_tone = 'orange'

            now = time.monotonic()
            if maintenance_future is None and capture_future is None and now - last_poll >= 5:
                maintenance_future = pool.submit(
                    maintain_camera, worker.store, api, detector, calibration, events.put,
                    worker,
                )
                last_poll = now
    finally:
        live.close()
