import secrets
from datetime import UTC, datetime
from uuid import uuid4

import psycopg

from ..application.errors import ApplicationError
from ..application.inspection_service import (
    capture_within_authorization,
    pairing_action,
    receipt_status,
)
from ..database import connection


def public_inspection(row):
    result = {
        key: row[key]
        for key in (
            'id',
            'device_id',
            'user_id',
            'operator_name',
            'state',
            'created_at',
            'pairing_expires_at',
            'started_at',
            'authorization_expires_at',
            'closed_at',
        )
    }
    now = row.get('observed_at') or datetime.now(UTC)
    result['observed_at'] = now
    deadline = (
        row['pairing_expires_at'] if row['state'] == 'pending' else row['authorization_expires_at']
    )
    if row['state'] in ('pending', 'active', 'closing') and deadline and deadline <= now:
        result['state'] = 'expired'
    return result


SESSION_SELECT = 'SELECT s.*,u.name AS operator_name,clock_timestamp() AS observed_at FROM orangevision_web.inspection_sessions s JOIN orangevision_web.users u ON u.id=s.user_id'


class InspectionRepository:
    def __init__(self, settings):
        self.settings = settings

    def devices(self, user_id):
        with connection(self.settings) as db:
            return db.execute(
                """SELECT d.id,d.nome AS name FROM public.dispositivos d
                JOIN orangevision_web.device_access a ON a.device_id=d.id WHERE a.user_id=%s ORDER BY d.nome,d.id""",
                (user_id,),
            ).fetchall()

    def current(self, user_id):
        with connection(self.settings) as db:
            rows = db.execute(
                SESSION_SELECT
                + " WHERE s.user_id=%s AND s.state IN ('pending','active','closing') ORDER BY s.created_at DESC",
                (user_id,),
            ).fetchall()
        return [
            public_inspection(row) for row in rows if public_inspection(row)['state'] != 'expired'
        ]

    def start(self, user_id, device_id, request_id, pairing_hash):
        with connection(self.settings) as db:
            device = db.execute(
                """SELECT d.id FROM public.dispositivos d JOIN orangevision_web.device_access a
                ON a.device_id=d.id WHERE d.id=%s AND a.user_id=%s FOR UPDATE OF d""",
                (device_id, user_id),
            ).fetchone()
            if not device:
                raise ApplicationError(403, 'Equipamento não autorizado para esta conta.')
            previous = db.execute(
                SESSION_SELECT + ' WHERE s.user_id=%s AND s.request_id=%s', (user_id, request_id)
            ).fetchone()
            if previous:
                if previous['device_id'] != device_id or previous['pairing_hash'] != pairing_hash:
                    raise ApplicationError(409, 'O comando já existe com outro conteúdo.')
                return public_inspection(previous)
            db.execute(
                """UPDATE orangevision_web.inspection_sessions SET state='expired',
                closed_at=COALESCE(authorization_expires_at,pairing_expires_at)
                WHERE device_id=%s AND state IN ('pending','active','closing') AND
                (CASE WHEN state='pending' THEN pairing_expires_at ELSE authorization_expires_at END)<=now()""",
                (device_id,),
            )
            if db.execute(
                "SELECT id FROM orangevision_web.inspection_sessions WHERE device_id=%s AND state IN ('pending','active','closing')",
                (device_id,),
            ).fetchone():
                raise ApplicationError(409, 'O equipamento já tem uma inspeção em andamento.')
            session_id = uuid4()
            inserted = db.execute(
                """INSERT INTO orangevision_web.inspection_sessions
                (id,user_id,device_id,request_id,state,pairing_hash,pairing_expires_at)
                VALUES (%s,%s,%s,%s,'pending',%s,now()+interval '5 minutes')
                ON CONFLICT DO NOTHING RETURNING id""",
                (session_id, user_id, device_id, request_id, pairing_hash),
            ).fetchone()
            if not inserted:
                raise ApplicationError(409, 'O comando ou código de pareamento já está em uso.')
            row = db.execute(SESSION_SELECT + ' WHERE s.id=%s', (session_id,)).fetchone()
        return public_inspection(row)

    def request_close(self, user_id, session_id):
        with connection(self.settings) as db:
            row = db.execute(
                SESSION_SELECT + ' WHERE s.id=%s AND s.user_id=%s FOR UPDATE OF s',
                (session_id, user_id),
            ).fetchone()
            if not row:
                raise ApplicationError(404, 'Inspeção não encontrada ou sem acesso.')
            if row['state'] == 'pending':
                db.execute(
                    "UPDATE orangevision_web.inspection_sessions SET state='closed',closed_at=now() WHERE id=%s",
                    (session_id,),
                )
            elif row['state'] == 'active':
                db.execute(
                    "UPDATE orangevision_web.inspection_sessions SET state='closing' WHERE id=%s",
                    (session_id,),
                )
            result = db.execute(SESSION_SELECT + ' WHERE s.id=%s', (session_id,)).fetchone()
        return public_inspection(result)

    def authenticate_device(self, token_hash):
        with connection(self.settings) as db:
            return db.execute(
                'SELECT device_id FROM orangevision_web.device_credentials WHERE token_hash=%s AND revoked_at IS NULL',
                (token_hash,),
            ).fetchone()

    def pair(self, device_id, pairing_hash, activation_id, lease_hash, lease_seconds):
        with connection(self.settings) as db:
            row = db.execute(
                SESSION_SELECT + ' WHERE s.device_id=%s AND s.pairing_hash=%s FOR UPDATE OF s',
                (device_id, pairing_hash),
            ).fetchone()
            if (
                pairing_action(
                    row,
                    device_id,
                    activation_id,
                    lease_hash,
                    row['observed_at'] if row else datetime.now(UTC),
                )
                == 'retry'
            ):
                return public_inspection(row)
            if not db.execute(
                'SELECT 1 FROM orangevision_web.device_access WHERE user_id=%s AND device_id=%s',
                (row['user_id'], device_id),
            ).fetchone():
                raise ApplicationError(403, 'Permissão de uso do equipamento foi removida.')
            db.execute(
                """UPDATE orangevision_web.inspection_sessions SET state='active',activation_id=%s,lease_hash=%s,
                started_at=now(),authorization_expires_at=now()+(%s * interval '1 second') WHERE id=%s""",
                (activation_id, lease_hash, lease_seconds, row['id']),
            )
            result = db.execute(SESSION_SELECT + ' WHERE s.id=%s', (row['id'],)).fetchone()
        return public_inspection(result)

    def _leased(self, db, device_id, session_id, lease_hash):
        row = db.execute(
            SESSION_SELECT + ' WHERE s.id=%s AND s.device_id=%s FOR UPDATE OF s',
            (session_id, device_id),
        ).fetchone()
        if (
            not row
            or not row['lease_hash']
            or not secrets.compare_digest(row['lease_hash'], lease_hash)
        ):
            raise ApplicationError(403, 'Autorização de inspeção inválida.')
        return row

    def device_session(self, device_id, session_id, lease_hash):
        with connection(self.settings) as db:
            row = self._leased(db, device_id, session_id, lease_hash)
        return public_inspection(row)

    def acknowledge_close(self, device_id, session_id, lease_hash):
        with connection(self.settings) as db:
            row = self._leased(db, device_id, session_id, lease_hash)
            if row['state'] in ('active', 'closing'):
                db.execute(
                    "UPDATE orangevision_web.inspection_sessions SET state='closed',closed_at=LEAST(now(),authorization_expires_at) WHERE id=%s",
                    (session_id,),
                )
            result = db.execute(SESSION_SELECT + ' WHERE s.id=%s', (session_id,)).fetchone()
        return public_inspection(result)

    def ingest(self, device_id, lease_hash, items):
        with connection(self.settings) as db:
            session = self._leased(db, device_id, items[0][0]['inspection_session_id'], lease_hash)
            if not session['started_at'] or not session['authorization_expires_at']:
                raise ApplicationError(403, 'Inspeção ainda não autorizada.')
            results = []
            for payload, payload_hash in items:
                timestamp = datetime.fromisoformat(payload['timestamp'])
                if not capture_within_authorization(timestamp, session, session['observed_at']):
                    results.append({'id': payload['id'], 'status': 'rejected'})
                    continue
                try:
                    with db.transaction():
                        metrics = payload['metrics']
                        inserted = db.execute(
                            """INSERT INTO public.analises
                            (id,dispositivo_id,data_hora,classificacao,cor_media,regioes_anormais,circularidade,assimetria,
                             score_visual,versao_algoritmo,criado_em,inspection_session_id,calibration_version,classification_reason)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s,%s,%s) ON CONFLICT(id) DO NOTHING RETURNING id""",
                            (
                                payload['id'],
                                device_id,
                                timestamp,
                                payload['classification'],
                                metrics['orange_color_ratio'] * 100,
                                metrics['abnormal_region_ratio'] * 100,
                                metrics['circularity'],
                                metrics['asymmetry'] * 100,
                                metrics['visual_score'],
                                payload['algorithm_version'],
                                session['id'],
                                payload['calibration_version'],
                                payload['reason'],
                            ),
                        ).fetchone()
                        if inserted:
                            db.execute(
                                'INSERT INTO orangevision_web.ingestion_receipts (analysis_id,inspection_session_id,payload_hash) VALUES (%s,%s,%s)',
                                (payload['id'], session['id'], payload_hash),
                            )
                            status = 'accepted'
                        else:
                            old = db.execute(
                                'SELECT inspection_session_id,payload_hash FROM orangevision_web.ingestion_receipts WHERE analysis_id=%s',
                                (payload['id'],),
                            ).fetchone()
                            status = receipt_status(old, session['id'], payload_hash)
                except (psycopg.IntegrityError, psycopg.DataError):
                    status = 'rejected'
                results.append({'id': payload['id'], 'status': status})
        # ACK somente depois do commit do lote; erro de commit não confirma itens.
        return results
