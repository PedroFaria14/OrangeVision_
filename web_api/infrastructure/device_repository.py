from uuid import UUID, uuid4

from ..application.auth_service import digest
from ..application.errors import ApplicationError
from ..database import connection


class DeviceRepository:
    def __init__(self, settings):
        self.settings = settings

    @staticmethod
    def _ready(db):
        return db.execute(
            """SELECT to_regclass('orangevision_web.managed_devices') IS NOT NULL
            AND to_regclass('orangevision_web.device_commands') IS NOT NULL
            AND to_regclass('orangevision_web.device_credentials') IS NOT NULL AS ready"""
        ).fetchone()['ready']

    @staticmethod
    def _device(db, user_id, device_id):
        row = db.execute(
            """SELECT d.id, d.nome AS name, d.criado_em AS created_at,
            (m.owner_id = %s) AS can_manage_credentials
            FROM public.dispositivos d
            JOIN orangevision_web.device_access a ON a.device_id = d.id AND a.user_id = %s
            LEFT JOIN orangevision_web.managed_devices m ON m.device_id = d.id
            WHERE d.id = %s""",
            (user_id, user_id, device_id),
        ).fetchone()
        if not row:
            raise ApplicationError(404, 'Equipamento não encontrado ou não autorizado.')
        row['can_manage_credentials'] = bool(row['can_manage_credentials'])
        return row

    def list_devices(self, user_id):
        with connection(self.settings) as db:
            db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            ready = self._ready(db)
            if ready:
                items = db.execute(
                    """SELECT d.id, d.nome AS name, d.criado_em AS created_at,
                    COALESCE(m.owner_id = %s, false) AS can_manage_credentials
                    FROM public.dispositivos d
                    JOIN orangevision_web.device_access a ON a.device_id = d.id AND a.user_id = %s
                    LEFT JOIN orangevision_web.managed_devices m ON m.device_id = d.id
                    ORDER BY d.criado_em DESC NULLS LAST, d.id""", (user_id, user_id),
                ).fetchall()
                count = db.execute(
                    'SELECT count(*) AS count FROM orangevision_web.managed_devices WHERE owner_id=%s',
                    (user_id,),
                ).fetchone()['count']
            else:
                items = db.execute(
                    """SELECT d.id, d.nome AS name, d.criado_em AS created_at,
                    false AS can_manage_credentials FROM public.dispositivos d
                    JOIN orangevision_web.device_access a ON a.device_id=d.id
                    WHERE a.user_id=%s ORDER BY d.criado_em DESC NULLS LAST, d.id""", (user_id,),
                ).fetchall()
                count = 0
        return {'items': items, 'registration_enabled': ready, 'managed_count': count}

    @staticmethod
    def _consume_limit(db, user_id):
        bucket = digest(f'device-management:{user_id}')
        row = db.execute(
            """INSERT INTO orangevision_web.auth_attempts(bucket,attempts,expires_at)
            VALUES (%s,1,now()+interval '15 minutes') ON CONFLICT(bucket) DO UPDATE SET
            attempts=CASE WHEN auth_attempts.expires_at<=now() THEN 1 ELSE auth_attempts.attempts+1 END,
            expires_at=CASE WHEN auth_attempts.expires_at<=now() THEN now()+interval '15 minutes'
            ELSE auth_attempts.expires_at END RETURNING attempts""", (bucket,),
        ).fetchone()
        if row['attempts'] > 10:
            raise ApplicationError(429, 'Muitas emissões. Aguarde 15 minutos.', {'Retry-After': '900'})

    def issue(self, user_id, request_id, operation, payload, fingerprint, token_hash, maximum):
        with connection(self.settings) as db:
            if not self._ready(db):
                raise ApplicationError(503, 'Cadastro de equipamentos requer a migration 006.')
            # Serializa quota e comandos da conta sem bloquear FKs de inspeções/sessões.
            db.execute(
                'SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                (f'device-management:{user_id}',),
            )
            command = db.execute(
                'SELECT * FROM orangevision_web.device_commands WHERE user_id=%s AND request_id=%s',
                (user_id, request_id),
            ).fetchone()
            if command:
                if command['operation'] != operation or command['fingerprint'] != fingerprint:
                    raise ApplicationError(409, 'O comando já foi utilizado com outros dados.')
                device = self._device(db, user_id, command['device_id'])
                if operation == 'rotate' and not device['can_manage_credentials']:
                    raise ApplicationError(404, 'Equipamento não encontrado ou não autorizado.')
                return device, True

            if operation == 'create':
                count = db.execute(
                    'SELECT count(*) AS count FROM orangevision_web.managed_devices WHERE owner_id=%s',
                    (user_id,),
                ).fetchone()['count']
                if count >= maximum:
                    raise ApplicationError(409, f'Limite de {maximum} equipamentos cadastrados atingido.')
                self._consume_limit(db, user_id)
                device_id = uuid4()
                db.execute(
                    "INSERT INTO public.dispositivos(id,nome,status,criado_em) VALUES (%s,%s,'offline',now())",
                    (device_id, payload['name']),
                )
                db.execute(
                    'INSERT INTO orangevision_web.device_access(user_id,device_id) VALUES (%s,%s)',
                    (user_id, device_id),
                )
                db.execute(
                    'INSERT INTO orangevision_web.managed_devices(device_id,owner_id) VALUES (%s,%s)',
                    (device_id, user_id),
                )
            else:
                device_id = UUID(payload['device_id'])
                device = self._device(db, user_id, device_id)
                if not device['can_manage_credentials']:
                    raise ApplicationError(404, 'Equipamento não encontrado ou não autorizado.')
                db.execute('SELECT id FROM public.dispositivos WHERE id=%s FOR UPDATE', (device_id,))
                self._consume_limit(db, user_id)
                db.execute(
                    'UPDATE orangevision_web.device_credentials SET revoked_at=now() '
                    'WHERE device_id=%s AND revoked_at IS NULL', (device_id,),
                )
            credential_id = uuid4()
            db.execute(
                'INSERT INTO orangevision_web.device_credentials(id,device_id,token_hash) VALUES (%s,%s,%s)',
                (credential_id, device_id, token_hash),
            )
            db.execute(
                """INSERT INTO orangevision_web.device_commands
                (user_id,request_id,operation,device_id,fingerprint,credential_id)
                VALUES (%s,%s,%s,%s,%s,%s)""",
                (user_id, request_id, operation, device_id, fingerprint, credential_id),
            )
            device = self._device(db, user_id, device_id)
        return device, False
