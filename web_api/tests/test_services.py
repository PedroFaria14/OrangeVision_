from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from web_api.api.dependencies import get_auth_service
from web_api.application.auth_service import AuthService, digest
from web_api.application.errors import ApplicationError
from web_api.application.query_service import QueryService
from web_api.contracts import Filters
from web_api.main import create_app

from .test_web_api import SETTINGS


class MemoryAuthStore:
    """Fake de fronteira para testar casos de uso; nunca usado pela aplicação real."""

    def __init__(self):
        self.users = {}
        self.sessions = {}
        self.attempts = {}

    def consume_attempts(self, bucket_hashes, maximum):
        for bucket in bucket_hashes:
            self.attempts[bucket] = self.attempts.get(bucket, 0) + 1
            if self.attempts[bucket] > maximum:
                return False
        return True

    def create_user(self, user_id, name, email, password_hash):
        if email in self.users:
            raise ApplicationError(409, 'Não foi possível cadastrar com os dados informados.')
        self.users[email] = {
            'id': user_id,
            'name': name,
            'email': email,
            'password_hash': password_hash,
        }

    def find_user(self, email):
        return self.users.get(email)

    def find_session(self, token_hash):
        stored = self.sessions.get(token_hash)
        if not stored or stored['expires_at'] <= datetime.now(UTC):
            return None
        user = next(user for user in self.users.values() if user['id'] == stored['user_id'])
        return {**user, 'csrf_token': stored['csrf_token']}

    def replace_session(self, old_hash, token_hash, user_id, csrf, expires_at):
        self.sessions.pop(old_hash, None)
        self.sessions[token_hash] = {
            'user_id': user_id,
            'csrf_token': csrf,
            'expires_at': expires_at,
        }

    def revoke_session(self, token_hash):
        self.sessions.pop(token_hash, None)


class StubPasswords:
    def hash_password(self, password):
        return 'test-only-password-hash'

    def verify_password(self, stored_hash, password):
        return stored_hash == 'test-only-password-hash' and password == 'a safe long passphrase'


@pytest.fixture
def auth_service():
    return AuthService(MemoryAuthStore(), StubPasswords(), 28800)


def register_user(service):
    return service.register('Pessoa', 'person@example.com', 'a safe long passphrase', 'test-client')


def test_registration_does_not_create_session_or_grant_devices(auth_service):
    assert register_user(auth_service) == {'message': 'Cadastro concluído. Entre para continuar.'}
    assert auth_service.store.sessions == {}
    record = auth_service.store.users['person@example.com']
    assert set(record) == {'id', 'name', 'email', 'password_hash'}


def test_rotation_revokes_old_session_and_never_exposes_hash(auth_service):
    register_user(auth_service)
    first = auth_service.login('person@example.com', 'a safe long passphrase', 'test-client', None)
    second = auth_service.login(
        'person@example.com', 'a safe long passphrase', 'test-client', first.token
    )
    assert digest(first.token) not in auth_service.store.sessions
    assert second.token not in auth_service.store.sessions
    assert digest(second.token) in auth_service.store.sessions
    assert 'password_hash' not in second.data['user']
    assert second.token not in repr(second)


@pytest.mark.parametrize(
    'email,password',
    [
        ('missing@example.com', 'a safe long passphrase'),
        ('person@example.com', 'incorrect password'),
    ],
)
def test_invalid_login_is_generic(auth_service, email, password):
    register_user(auth_service)
    with pytest.raises(ApplicationError) as result:
        auth_service.login(email, password, 'test-client', None)
    assert result.value.status_code == 401
    assert result.value.detail == 'E-mail ou senha inválidos.'


def test_service_session_expiry_and_logout(auth_service):
    register_user(auth_service)
    issued = auth_service.login('person@example.com', 'a safe long passphrase', 'test-client', None)
    assert auth_service.session(issued.token) == issued.data
    auth_service.store.sessions[digest(issued.token)]['expires_at'] = datetime.now(UTC) - timedelta(
        seconds=1
    )
    with pytest.raises(ApplicationError) as result:
        auth_service.session(issued.token)
    assert result.value.status_code == 401
    auth_service.logout(issued.token)
    assert not auth_service.store.sessions


def test_rate_limit_uses_hashed_buckets_and_preserves_retry_after(auth_service):
    for _ in range(10):
        auth_service.limit_attempts('test-client', 'person@example.com')
    with pytest.raises(ApplicationError) as result:
        auth_service.limit_attempts('test-client', 'person@example.com')
    assert result.value.status_code == 429
    assert result.value.headers == {'Retry-After': '900'}
    assert 'person@example.com' not in repr(auth_service.store.attempts)


def test_auth_http_flow_with_injected_store_not_neon(auth_service):
    app = create_app(SETTINGS)
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    payload = {'email': 'person@example.com', 'password': 'a safe long passphrase'}
    origin = {'Origin': 'http://localhost:5173'}
    with TestClient(app) as client:
        assert (
            client.post(
                '/api/auth/register', json={**payload, 'name': 'Pessoa'}, headers=origin
            ).status_code
            == 201
        )
        login = client.post('/api/auth/login', json=payload, headers=origin)
        assert login.status_code == 200
        cookie = login.headers['set-cookie']
        assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie and 'Path=/api' in cookie
        assert client.get('/api/auth/session').json() == login.json()
        assert client.post('/api/auth/logout', headers=origin).status_code == 403
        assert (
            client.post(
                '/api/auth/logout', headers={**origin, 'X-CSRF-Token': login.json()['csrf_token']}
            ).status_code
            == 204
        )
        assert client.get('/api/auth/session').status_code == 401


class EmptyAnalysisReader:
    def summarize(self, user_id, filters):
        return {'total': 0, 'approved': 0, 'attention': 0, 'review': 0, 'latest_analysis_at': None}

    def find_analysis(self, user_id, analysis_id):
        return None


def test_summary_zero_has_no_measured_rate():
    result = QueryService(EmptyAnalysisReader()).summary(UUID(int=1), Filters())
    assert result['approval_rate'] is None
    assert result['total'] == 0


def test_detail_hides_missing_or_unauthorized_resource():
    with pytest.raises(ApplicationError) as result:
        QueryService(EmptyAnalysisReader()).detail(UUID(int=1), UUID(int=2))
    assert result.value.status_code == 404


def test_timeseries_rejects_unbounded_period_before_repository():
    with pytest.raises(ApplicationError) as result:
        QueryService(EmptyAnalysisReader()).timeseries(UUID(int=1), Filters())
    assert result.value.status_code == 422
    assert result.value.detail[0]['field'] == 'period'
