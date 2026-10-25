import secrets
from datetime import timedelta
from uuid import uuid4

from psycopg.types.json import Jsonb

from ..application.errors import ApplicationError
from ..application.inspection_service import capture_within_authorization
from ..database import connection

COLUMNS = """s.id,s.filename,s.width,s.height,s.state,s.device_id,s.metrics,s.classification,
s.reason,s.calibration_version,s.algorithm_version,s.created_at,s.updated_at,
s.started_at,s.finished_at,s.claim_expires_at,s.detection,s.source_inspection_id,s.captured_at,s.review_authorization_id,(s.mask_data IS NOT NULL) AS has_mask"""


def public_sample(row):
    result = {key: value for key, value in row.items() if key != 'has_mask'}
    result['image_url'] = f'/api/samples/{row["id"]}/image'
    result['mask_url'] = f'/api/samples/{row["id"]}/mask' if row['has_mask'] else None
    return result


class SampleRepository:
    def __init__(self, settings):
        self.settings = settings

    def ready(self):
        with connection(self.settings) as db:
            return db.execute(
                "SELECT to_regclass('orangevision_web.image_samples') IS NOT NULL AND to_regclass('orangevision_web.sample_executors') IS NOT NULL AND EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='orangevision_web' AND table_name='image_samples' AND column_name='review_authorization_id') AS ready"
            ).fetchone()['ready']

    def devices(self, owner):
        with connection(self.settings) as db:
            return db.execute(
                "SELECT d.id,d.nome AS name,e.last_seen_at,e.state AS executor_state,e.message AS executor_message,e.model_version,COALESCE(e.last_seen_at > clock_timestamp()-interval '30 seconds',false) AS executor_recent FROM public.dispositivos d JOIN orangevision_web.device_access a ON a.device_id=d.id LEFT JOIN orangevision_web.sample_executors e ON e.device_id=d.id WHERE a.user_id=%s ORDER BY d.nome,d.id",
                (owner,),
            ).fetchall()

    def heartbeat(self, device, payload):
        with connection(self.settings) as db:
            return db.execute(
                'INSERT INTO orangevision_web.sample_executors(device_id,last_seen_at,state,model_version,message) VALUES (%s,clock_timestamp(),%s,%s,%s) ON CONFLICT(device_id) DO UPDATE SET last_seen_at=clock_timestamp(),state=excluded.state,model_version=excluded.model_version,message=excluded.message RETURNING last_seen_at',
                (device, payload['state'], payload['model_version'], payload['message']),
            ).fetchone()

    def authenticate_device(self, token_hash):
        with connection(self.settings) as db:
            return db.execute(
                'SELECT device_id FROM orangevision_web.device_credentials WHERE token_hash=%s AND revoked_at IS NULL',
                (token_hash,),
            ).fetchone()

    def _read(self, db, identity):
        return public_sample(
            db.execute(
                f'SELECT {COLUMNS} FROM orangevision_web.image_samples s WHERE s.id=%s', (identity,)
            ).fetchone()
        )

    def _review_owner(
        self, db, device, original_id, original_hash, review_id, review_hash, captured_at=None
    ):
        identities = [identity for identity in (original_id, review_id) if identity is not None]
        rows = db.execute(
            'SELECT s.*,clock_timestamp() AS observed_at FROM orangevision_web.inspection_sessions s WHERE s.device_id=%s AND s.id=ANY(%s) ORDER BY s.id FOR SHARE OF s',
            (device, identities),
        ).fetchall()
        grants = {row['id']: row for row in rows}
        review = grants.get(review_id)
        if (
            not review
            or not secrets.compare_digest(review['lease_hash'] or '', review_hash or '')
            or review['state'] != 'active'
            or not review['started_at']
            or not review['authorization_expires_at']
            or not review['started_at']
            <= review['observed_at']
            < review['authorization_expires_at']
        ):
            raise ApplicationError(403, 'A nova sessão não autoriza o envio da foto.')
        if original_id is not None:
            original = grants.get(original_id)
            if (
                not original
                or not secrets.compare_digest(original['lease_hash'] or '', original_hash or '')
                or original['user_id'] != review['user_id']
            ):
                raise ApplicationError(
                    403, 'A foto só pode ser recuperada pela conta do operador original.'
                )
        if captured_at is not None and captured_at > review['observed_at'] + timedelta(seconds=30):
            raise ApplicationError(422, 'Horário da foto está no futuro. Confira UTC/NTP.')
        if not db.execute(
            'SELECT 1 FROM orangevision_web.device_access WHERE user_id=%s AND device_id=%s',
            (review['user_id'], device),
        ).fetchone():
            raise ApplicationError(403, 'Equipamento não autorizado para a conta da foto.')
        return review['user_id']

    def authorize_review(self, device, original_id, original_hash, review_id, review_hash):
        with connection(self.settings) as db:
            self._review_owner(db, device, original_id, original_hash, review_id, review_hash)

    def upload(
        self,
        owner,
        request_id,
        source_hash,
        filename,
        image,
        width,
        height,
        *,
        inspection_id=None,
        captured_at=None,
        device=None,
        lease_hash=None,
        review_authorization_id=None,
        review_lease_hash=None,
    ):
        with connection(self.settings) as db:
            if device is not None and review_authorization_id is not None:
                owner = self._review_owner(
                    db,
                    device,
                    inspection_id,
                    lease_hash,
                    review_authorization_id,
                    review_lease_hash,
                    captured_at,
                )
            elif device is not None:
                grant = db.execute(
                    'SELECT s.*,clock_timestamp() AS observed_at FROM orangevision_web.inspection_sessions s WHERE s.id=%s AND s.device_id=%s FOR UPDATE OF s',
                    (inspection_id, device),
                ).fetchone()
                if not grant or not secrets.compare_digest(
                    grant['lease_hash'] or '', lease_hash or ''
                ):
                    raise ApplicationError(403, 'Autorização de captura incompatível.')
                if not capture_within_authorization(captured_at, grant, grant['observed_at']):
                    raise ApplicationError(409, 'A captura está fora da janela autorizada.')
                owner = grant['user_id']
                if not db.execute(
                    'SELECT 1 FROM orangevision_web.device_access WHERE user_id=%s AND device_id=%s',
                    (owner, device),
                ).fetchone():
                    raise ApplicationError(403, 'Vínculo do equipamento removido.')
            # Serializa cota/idempotência da conta, sem bloquear outros usuários.
            db.execute('SELECT id FROM orangevision_web.users WHERE id=%s FOR UPDATE', (owner,))
            previous = db.execute(
                'SELECT id,source_hash,source_inspection_id,captured_at FROM orangevision_web.image_samples WHERE user_id=%s AND request_id=%s',
                (owner, request_id),
            ).fetchone()
            if previous:
                if previous['source_hash'] != source_hash:
                    raise ApplicationError(409, 'Este envio já existe com outro arquivo.')
                if device is not None and (
                    previous['source_inspection_id'] != inspection_id
                    or previous['captured_at'] != captured_at
                ):
                    raise ApplicationError(
                        409, 'Identidade de captura já utilizada com outra autorização.'
                    )
                return self._read(db, previous['id'])
            if (
                db.execute(
                    'SELECT count(*) AS total FROM orangevision_web.image_samples WHERE user_id=%s',
                    (owner,),
                ).fetchone()['total']
                >= 200
            ):
                raise ApplicationError(409, 'Limite de 200 amostras por conta atingido.')
            identity = uuid4()
            db.execute(
                'INSERT INTO orangevision_web.image_samples(id,user_id,request_id,source_hash,filename,image_data,width,height,state,device_id,source_inspection_id,captured_at,review_authorization_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (
                    identity,
                    owner,
                    request_id,
                    source_hash,
                    filename,
                    image,
                    width,
                    height,
                    'queued' if device is not None else 'received',
                    device,
                    inspection_id,
                    captured_at,
                    review_authorization_id,
                ),
            )
            return self._read(db, identity)

    def listing(self, owner, limit, offset):
        with connection(self.settings) as db:
            db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            rows = db.execute(
                f'SELECT {COLUMNS} FROM orangevision_web.image_samples s WHERE user_id=%s ORDER BY created_at DESC,id DESC LIMIT %s OFFSET %s',
                (owner, limit, offset),
            ).fetchall()
            total = db.execute(
                'SELECT count(*) AS total FROM orangevision_web.image_samples WHERE user_id=%s',
                (owner,),
            ).fetchone()['total']
            return {'items': [public_sample(row) for row in rows], 'total': total}

    def image(self, owner, identity, mask):
        column = 'mask_data' if mask else 'image_data'
        with connection(self.settings) as db:
            row = db.execute(
                f'SELECT {column} AS content FROM orangevision_web.image_samples WHERE id=%s AND user_id=%s',
                (identity, owner),
            ).fetchone()
            if not row or row['content'] is None:
                raise ApplicationError(404, 'Imagem não encontrada ou sem acesso.')
            return bytes(row['content'])

    def queue(self, owner, identity, device):
        with connection(self.settings) as db:
            row = db.execute(
                'SELECT state,device_id,claim_expires_at,clock_timestamp() AS now FROM orangevision_web.image_samples WHERE id=%s AND user_id=%s FOR UPDATE',
                (identity, owner),
            ).fetchone()
            if not row:
                raise ApplicationError(404, 'Amostra não encontrada ou sem acesso.')
            if not db.execute(
                'SELECT 1 FROM orangevision_web.device_access WHERE user_id=%s AND device_id=%s',
                (owner, device),
            ).fetchone():
                raise ApplicationError(403, 'Equipamento não autorizado para esta conta.')
            if (
                row['state'] == 'processing'
                and row['claim_expires_at']
                and row['claim_expires_at'] > row['now']
            ):
                raise ApplicationError(
                    409,
                    'Amostra já está em processamento. Aguarde o resultado ou vencimento da reserva.',
                )
            if row['state'] == 'queued' and row['device_id'] == device:
                return self._read(db, identity)
            db.execute(
                "UPDATE orangevision_web.image_samples SET state='queued',device_id=%s,claim_id=NULL,lease_hash=NULL,claim_expires_at=NULL,metrics=NULL,classification=NULL,reason=NULL,calibration_version=NULL,algorithm_version=NULL,mask_data=NULL,detection=NULL,result_hash=NULL,started_at=NULL,finished_at=NULL,updated_at=clock_timestamp() WHERE id=%s",
                (device, identity),
            )
            return self._read(db, identity)

    def claim(self, device, claim_id, lease_hash):
        with connection(self.settings) as db:
            # Serializa a recuperação de uma mesma claim antes da escolha da fila.
            db.execute(
                'SELECT id FROM public.dispositivos WHERE id=%s FOR NO KEY UPDATE', (device,)
            )
            previous = db.execute(
                'SELECT id,device_id,lease_hash,state,claim_expires_at,clock_timestamp() AS now FROM orangevision_web.image_samples WHERE claim_id=%s FOR UPDATE',
                (claim_id,),
            ).fetchone()
            if previous:
                if previous['device_id'] != device or not secrets.compare_digest(
                    previous['lease_hash'] or '', lease_hash
                ):
                    raise ApplicationError(409, 'Reserva incompatível.')
                if (
                    previous['state'] == 'processing'
                    and previous['claim_expires_at'] > previous['now']
                ):
                    self._assignment(db, device, previous['id'], lease_hash, claim_id)
                    return self._read(db, previous['id'])
                return None
            row = db.execute(
                "SELECT s.id FROM orangevision_web.image_samples s WHERE s.device_id=%s AND EXISTS (SELECT 1 FROM orangevision_web.device_access a WHERE a.user_id=s.user_id AND a.device_id=s.device_id) AND (s.state='queued' OR (s.state='processing' AND s.claim_expires_at<=clock_timestamp())) ORDER BY s.created_at,s.id FOR UPDATE OF s SKIP LOCKED LIMIT 1",
                (device,),
            ).fetchone()
            if not row:
                return None
            db.execute(
                "UPDATE orangevision_web.image_samples SET state='processing',claim_id=%s,lease_hash=%s,claim_expires_at=clock_timestamp()+interval '5 minutes',started_at=clock_timestamp(),updated_at=clock_timestamp() WHERE id=%s",
                (claim_id, lease_hash, row['id']),
            )
            return self._read(db, row['id'])

    def _assignment(self, db, device, identity, lease_hash, claim_id=None, allow_finished=False):
        row = db.execute(
            'SELECT s.id,s.width,s.height,s.state,s.claim_id,s.lease_hash,s.claim_expires_at,s.result_hash,clock_timestamp() AS now FROM orangevision_web.image_samples s WHERE s.id=%s AND s.device_id=%s AND EXISTS (SELECT 1 FROM orangevision_web.device_access a WHERE a.user_id=s.user_id AND a.device_id=s.device_id) FOR UPDATE OF s',
            (identity, device),
        ).fetchone()
        if (
            not row
            or not secrets.compare_digest(row['lease_hash'] or '', lease_hash)
            or (claim_id is not None and row['claim_id'] != claim_id)
        ):
            raise ApplicationError(404, 'Amostra não encontrada ou sem acesso.')
        if allow_finished and row['result_hash']:
            return row
        if row['state'] != 'processing' or row['claim_expires_at'] <= row['now']:
            raise ApplicationError(409, 'Reserva vencida ou processamento não ativo.')
        return row

    def assignment(self, device, identity, claim_id, lease_hash):
        with connection(self.settings) as db:
            return self._assignment(db, device, identity, lease_hash, claim_id, allow_finished=True)

    def device_image(self, device, identity, lease_hash):
        with connection(self.settings) as db:
            self._assignment(db, device, identity, lease_hash)
            return bytes(
                db.execute(
                    'SELECT image_data FROM orangevision_web.image_samples WHERE id=%s', (identity,)
                ).fetchone()['image_data']
            )

    def finish(self, device, identity, lease_hash, payload, payload_hash, mask):
        from uuid import UUID

        with connection(self.settings) as db:
            row = self._assignment(
                db, device, identity, lease_hash, UUID(payload['claim_id']), allow_finished=True
            )
            if row['result_hash']:
                if row['result_hash'] != payload_hash:
                    raise ApplicationError(409, 'Resultado divergente para a mesma reserva.')
                return self._read(db, identity)
            db.execute(
                'UPDATE orangevision_web.image_samples SET state=%s,metrics=%s,classification=%s,reason=%s,calibration_version=%s,algorithm_version=%s,mask_data=%s,detection=%s,result_hash=%s,finished_at=clock_timestamp(),updated_at=clock_timestamp() WHERE id=%s',
                (
                    payload['state'],
                    Jsonb(payload['metrics']) if payload['metrics'] is not None else None,
                    payload['classification'],
                    payload['reason'],
                    payload['calibration_version'],
                    payload['algorithm_version'],
                    mask,
                    Jsonb(payload['detection']) if payload.get('detection') is not None else None,
                    payload_hash,
                    identity,
                ),
            )
            return self._read(db, identity)
