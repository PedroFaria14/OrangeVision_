from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from web_api.api.dependencies import current_session
from web_api.api.device_routes import get_device_service
from web_api.application.auth_service import digest
from web_api.application.device_service import DeviceService
from web_api.application.errors import ApplicationError
from web_api.main import create_app

from .test_web_api import SETTINGS

USER = UUID(int=1)
DEVICE = UUID(int=10)
ORIGIN = 'http://localhost:5173'
HEADERS = {'Origin': ORIGIN, 'X-CSRF-Token': 'fixture-csrf'}


class DeviceBoundary:
    def __init__(self):
        self.calls = []
        self.replayed = False
        self.failure = None
        self.device = {
            'id': DEVICE, 'name': 'Raspberry de teste',
            'created_at': datetime.now(UTC), 'can_manage_credentials': True,
        }

    def list_devices(self, user_id):
        self.calls.append(('list', user_id))
        return {'items': [], 'registration_enabled': True, 'managed_count': 0}

    def issue(self, *args):
        self.calls.append(args)
        if self.failure:
            raise self.failure
        return self.device, self.replayed


@pytest.fixture
def device_http():
    store = DeviceBoundary()
    service = DeviceService(store, 5, 'https://api.example.test')
    app = create_app(SETTINGS)
    app.dependency_overrides[current_session] = lambda: {
        'user': {'id': USER, 'name': 'Pessoa', 'email': 'fixture@example.com'},
        'csrf_token': 'fixture-csrf',
    }
    app.dependency_overrides[get_device_service] = lambda: service
    with TestClient(app) as client:
        yield client, store


def test_device_routes_require_normal_session_without_database():
    with TestClient(create_app(SETTINGS)) as client:
        assert client.get('/api/devices').status_code == 401
        assert client.post('/api/devices', json={
            'name': 'Pi de teste', 'request_id': str(uuid4()),
        }).status_code == 401


def test_private_list_has_no_credentials(device_http):
    client, store = device_http
    response = client.get('/api/devices')
    assert response.status_code == 200
    assert response.json() == {
        'items': [], 'registration_enabled': True, 'managed_count': 0,
        'max_devices': 5, 'api_base_url': 'https://api.example.test',
    }
    assert store.calls == [('list', USER)]
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('path', ['/api/devices', f'/api/devices/{DEVICE}/credentials'])
def test_device_mutations_require_origin_and_csrf(device_http, path):
    client, store = device_http
    payload = {'request_id': str(uuid4())}
    if path == '/api/devices':
        payload['name'] = 'Raspberry'
    for headers in [{}, {'Origin': ORIGIN}, {'Origin': 'https://evil.example', 'X-CSRF-Token': 'fixture-csrf'}]:
        assert client.post(path, json=payload, headers=headers).status_code == 403
    assert not store.calls


def test_device_creation_is_bound_to_session_and_secret_is_one_time(device_http, caplog):
    client, store = device_http
    payload = {'request_id': str(uuid4()), 'name': '  Raspberry  '}
    response = client.post('/api/devices', json=payload, headers=HEADERS)
    assert response.status_code == 201
    result = response.json()
    secret = result['credential']
    assert len(secret) >= 32
    assert result['replayed'] is False
    call = store.calls[0]
    assert call[0] == USER
    assert call[3] == {'name': 'Raspberry'}
    assert call[5] == digest(secret)
    assert secret not in repr(store.calls) and secret not in caplog.text
    assert response.headers['cache-control'] == 'no-store'
    store.replayed = True
    replay = client.post('/api/devices', json=payload, headers=HEADERS)
    assert replay.status_code == 200
    assert replay.json()['credential'] is None
    assert replay.json()['replayed'] is True


def test_issued_dataclass_hides_secret_from_repr():
    result = DeviceService(DeviceBoundary()).register(USER, uuid4(), 'Raspberry')
    assert result.credential not in repr(result)


@pytest.mark.parametrize('extra', [{'user_id': str(UUID(int=2))}, {'device_id': str(DEVICE)}, {'status': 'online'}, {'credential': 'private-fixture'}])
def test_cannot_supply_owner_existing_device_status_or_secret(device_http, extra):
    client, store = device_http
    response = client.post('/api/devices', json={
        'request_id': str(uuid4()), 'name': 'Raspberry', **extra,
    }, headers=HEADERS)
    assert response.status_code == 422
    assert not store.calls
    assert 'private-fixture' not in response.text


@pytest.mark.parametrize('name', ['', ' ', 'a', 'a' * 101, 'Pi\nBancada'])
def test_device_name_validation(device_http, name):
    client, store = device_http
    assert client.post('/api/devices', json={
        'request_id': str(uuid4()), 'name': name,
    }, headers=HEADERS).status_code == 422
    assert not store.calls


def test_rotation_and_replay_use_same_endpoint_contract(device_http):
    client, store = device_http
    payload = {'request_id': str(uuid4())}
    response = client.post(f'/api/devices/{DEVICE}/credentials', json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()['credential']
    assert store.calls[0][2:4] == ('rotate', {'device_id': str(DEVICE)})
    store.replayed = True
    assert client.post(f'/api/devices/{DEVICE}/credentials', json=payload, headers=HEADERS).json()['credential'] is None


def test_conflict_missing_migration_and_rate_limit_propagate_safely(device_http):
    client, store = device_http
    for status in [404, 409, 429, 503]:
        store.failure = ApplicationError(status, 'Operação recusada.', {'Retry-After': '900'} if status == 429 else None)
        response = client.post('/api/devices', json={
            'request_id': str(uuid4()), 'name': 'Raspberry',
        }, headers=HEADERS)
        assert response.status_code == status
        assert response.json() == {'detail': 'Operação recusada.'}
        if status == 429:
            assert response.headers['retry-after'] == '900'


def test_device_request_has_real_body_limit(device_http):
    client, store = device_http
    response = client.post('/api/devices', content=b' ' * 16385, headers={**HEADERS, 'Content-Type': 'application/json'})
    assert response.status_code == 413
    assert not store.calls
