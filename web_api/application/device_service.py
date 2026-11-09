import json
import secrets
from dataclasses import dataclass, field
from uuid import UUID

from .auth_service import digest
from .ports import DeviceStore


@dataclass(frozen=True)
class IssuedDeviceCredential:
    device: dict
    credential: str | None = field(repr=False)
    replayed: bool


class DeviceService:
    def __init__(self, store: DeviceStore, maximum=5, api_base_url=None):
        self.store = store
        self.maximum = maximum
        self.api_base_url = api_base_url

    def list_devices(self, user_id: UUID):
        return {
            **self.store.list_devices(user_id),
            'max_devices': self.maximum,
            'api_base_url': self.api_base_url,
        }

    def _issue(self, user_id, request_id, operation, payload):
        fingerprint = digest(json.dumps(payload, sort_keys=True, separators=(',', ':')))
        token = secrets.token_urlsafe(32)
        device, replayed = self.store.issue(
            user_id, request_id, operation, payload, fingerprint, digest(token), self.maximum
        )
        # O hash não permite recuperar o segredo: retries retornam apenas metadados.
        return IssuedDeviceCredential(device, None if replayed else token, replayed)

    def register(self, user_id: UUID, request_id: UUID, name: str):
        return self._issue(user_id, request_id, 'create', {'name': name})

    def rotate(self, user_id: UUID, device_id: UUID, request_id: UUID):
        return self._issue(user_id, request_id, 'rotate', {'device_id': str(device_id)})
