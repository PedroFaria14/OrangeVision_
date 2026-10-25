"""Operação administrativa local. Nenhum cadastro de hardware é exposto ao navegador."""

import argparse
import secrets
from uuid import UUID, uuid4

from .application.auth_service import digest
from .config import Settings
from .database import connection


def main():
    parser = argparse.ArgumentParser(
        description='Provisionar equipamento/credencial/vínculo explícito.'
    )
    parser.add_argument(
        '--device', type=UUID, help='UUID existente; sem ele, cria novo equipamento.'
    )
    parser.add_argument('--name', default='Bancada OrangeVision')
    parser.add_argument('--user', type=UUID, help='Conta específica a autorizar, opcional.')
    parser.add_argument(
        '--grant-only',
        action='store_true',
        help='Somente vínculo; exige --device e --user, sem emitir outra credencial.',
    )
    parser.add_argument('--revoke', type=UUID, help='ID da credencial específica a revogar.')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print(
            'Plano somente. --apply executa no banco configurado. Credenciais não são emitidas sem aprovação.'
        )
        return
    try:
        settings = Settings.load()
        if args.grant_only and (not args.device or not args.user or args.revoke):
            raise RuntimeError('Vínculo exige --device e --user, sem --revoke.')
        with connection(settings) as db:
            if not db.execute(
                "SELECT to_regclass('orangevision_web.device_credentials') IS NOT NULL AS ready"
            ).fetchone()['ready']:
                raise RuntimeError('Aplique/revise a migration 002 antes de provisionar.')
            if args.revoke:
                changed = db.execute(
                    'UPDATE orangevision_web.device_credentials SET revoked_at=now() WHERE id=%s RETURNING id',
                    (args.revoke,),
                ).fetchone()
                if not changed:
                    raise RuntimeError('Credencial não encontrada.')
                print('Revogação registrada; confirmação ocorre ao finalizar a transação.')
                return
            device_id = args.device or uuid4()
            if args.device:
                if not db.execute(
                    'SELECT id FROM public.dispositivos WHERE id=%s', (device_id,)
                ).fetchone():
                    raise RuntimeError('Equipamento não encontrado.')
            else:
                db.execute(
                    "INSERT INTO public.dispositivos(id,nome,status,criado_em) VALUES (%s,%s,'offline',now())",
                    (device_id, args.name),
                )
            if args.user:
                db.execute(
                    'INSERT INTO orangevision_web.device_access(user_id,device_id) VALUES (%s,%s) ON CONFLICT DO NOTHING',
                    (args.user, device_id),
                )
            if args.grant_only:
                print('Vínculo específico registrado; nenhuma credencial adicional foi emitida.')
                return
            credential_id, token = uuid4(), secrets.token_urlsafe(32)
            db.execute(
                'INSERT INTO orangevision_web.device_credentials(id,device_id,token_hash) VALUES (%s,%s,%s)',
                (credential_id, device_id, digest(token)),
            )
        print(f'DEVICE_ID={device_id}')
        print(f'CREDENTIAL_ID={credential_id}')
        print('Segredo emitido uma única vez. Guarde somente no ambiente privado do equipamento:')
        print(f'DEVICE_INGEST_CREDENTIAL={token}')
    except Exception as exc:
        print(
            f'Provisionamento não confirmado; tipo={type(exc).__name__}. Nenhuma conexão é exibida.'
        )
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
