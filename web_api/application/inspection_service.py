import hashlib
import json
import secrets
from datetime import UTC, timedelta

from .auth_service import digest
from .errors import ApplicationError


def payload_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    ).hexdigest()


def pairing_action(row, device_id, activation_id, lease_hash, now):
    if not row or row['device_id'] != device_id:
        raise ApplicationError(404, 'Pareamento inválido ou indisponível.')
    if (
        row['activation_id'] == activation_id
        and row['lease_hash']
        and secrets.compare_digest(row['lease_hash'], lease_hash)
    ):
        return 'retry'
    if row['state'] != 'pending' or row['pairing_expires_at'] <= now:
        raise ApplicationError(409, 'Pareamento expirado ou já utilizado.')
    return 'activate'


def capture_within_authorization(timestamp, session, now):
    if not session['started_at'] or not session['authorization_expires_at']:
        return False
    deadline = min(
        session['authorization_expires_at'],
        session['closed_at'] + timedelta(seconds=30)
        if session['closed_at']
        else session['authorization_expires_at'],
    )
    return session['started_at'] - timedelta(
        seconds=30
    ) <= timestamp < deadline and timestamp <= now + timedelta(seconds=30)


def receipt_status(receipt, session_id, payload_hash):
    return (
        'duplicate'
        if receipt
        and str(receipt['inspection_session_id']) == str(session_id)
        and receipt['payload_hash'] == payload_hash
        else 'conflict'
    )


class InspectionService:
    def __init__(self, store, lease_seconds=28800):
        self.store = store
        self.lease_seconds = lease_seconds

    def devices(self, user_id):
        return self.store.devices(user_id)

    def current(self, user_id):
        return self.store.current(user_id)

    def start(self, user_id, device_id, request_id, pairing_code):
        return self.store.start(user_id, device_id, request_id, digest(pairing_code))

    def request_close(self, user_id, session_id):
        return self.store.request_close(user_id, session_id)

    def authenticate_device(self, token):
        if not token or len(token) > 256:
            raise ApplicationError(401, 'Credencial de dispositivo ausente ou inválida.')
        device = self.store.authenticate_device(digest(token))
        if not device:
            raise ApplicationError(401, 'Credencial de dispositivo ausente ou inválida.')
        return device

    def pair(self, device_id, pairing_code, activation_id, lease_token):
        return self.store.pair(
            device_id, digest(pairing_code), activation_id, digest(lease_token), self.lease_seconds
        )

    def device_session(self, device_id, session_id, lease_token):
        return self.store.device_session(device_id, session_id, digest(lease_token))

    def acknowledge_close(self, device_id, session_id, lease_token):
        return self.store.acknowledge_close(device_id, session_id, digest(lease_token))

    def ingest(self, device_id, lease_token, items):
        normalized = []
        for item in items:
            payload = item.model_dump(mode='json')
            payload['timestamp'] = item.timestamp.astimezone(UTC).isoformat()
            normalized.append((payload, payload_digest(payload)))
        return {'items': self.store.ingest(device_id, digest(lease_token), normalized)}
