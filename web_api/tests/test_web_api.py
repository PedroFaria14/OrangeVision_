"""Testes de contrato/segurança sem acessar o Neon do projeto."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from web_api import auth, queries
from web_api.application.auth_service import AuthService
from web_api.application.errors import ApplicationError
from web_api.config import Settings
from web_api.contracts import Filters, Registration
from web_api.infrastructure import auth_repository
from web_api.infrastructure.passwords import PasswordSecurity
from web_api.main import create_app

SETTINGS = Settings(
    'postgresql://unused:unused@localhost/unused', ('http://localhost:5173',), False, 28800
)


@pytest.fixture
def client():
    with TestClient(create_app(SETTINGS)) as value:
        yield value


@pytest.mark.parametrize(
    'path',
    [
        '/api/auth/session',
        '/api/analyses',
        '/api/metrics/summary',
        '/api/metrics/distribution',
        '/api/metrics/timeseries',
        '/api/analyses/00000000-0000-4000-8000-000000000001',
    ],
)
def test_private_routes_require_session(client, path):
    assert client.get(path).status_code == 401


def test_registration_rejects_short_password_without_echoing_secret(client):
    response = client.post(
        '/api/auth/register',
        json={'name': 'Pessoa', 'email': 'person@example.com', 'password': 'secret'},
    )
    assert response.status_code == 422
    assert 'secret' not in response.text
    assert response.json()['detail'][0]['field'] == 'password'


def test_registration_rejects_untrusted_origin_before_database(client):
    response = client.post(
        '/api/auth/register',
        headers={'Origin': 'https://untrusted.example'},
        json={
            'name': 'Pessoa',
            'email': 'person@example.com',
            'password': 'a safe long passphrase',
        },
    )
    assert response.status_code == 403


def test_cors_preflight_and_cache_headers(client):
    response = client.options('/api/auth/login', headers={'Origin': 'http://localhost:5173'})
    assert response.status_code == 204
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert response.headers['access-control-allow-credentials'] == 'true'
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-request-id']


def test_invalid_period_returns_validation_error(client):
    client.app.dependency_overrides[auth.current_session] = lambda: {'user': {'id': UUID(int=1)}}
    response = client.get('/api/analyses?start=2026-10-20T00:00:00Z&end=2026-10-19T00:00:00Z')
    assert response.status_code == 422


def test_query_parameters_are_flat_in_openapi(client):
    spec = client.app.openapi()
    params = {p['name'] for p in spec['paths']['/api/analyses']['get']['parameters']}
    assert params == {'start', 'end', 'classification', 'device_id', 'limit', 'offset'}
    assert spec['openapi'] == '3.1.0'


def test_logout_rejects_invalid_csrf_before_database(client):
    client.app.dependency_overrides[auth.current_session] = lambda: {'csrf_token': 'expected'}
    response = client.post(
        '/api/auth/logout', headers={'Origin': 'http://localhost:5173', 'X-CSRF-Token': 'incorrect'}
    )
    assert response.status_code == 403


def test_session_lookup_hashes_token_and_checks_expiry(client, monkeypatch):
    from contextlib import contextmanager

    calls = []

    class Database:
        def execute(self, sql, params):
            calls.append((sql, params))
            return self

        def fetchone(self):
            return None

    @contextmanager
    def fake_connection(settings):
        yield Database()

    monkeypatch.setattr(auth_repository, 'connection', fake_connection)
    service = AuthService(auth_repository.AuthRepository(SETTINGS), PasswordSecurity(), 28800)
    with pytest.raises(ApplicationError) as result:
        service.session('raw-session-token')
    assert result.value.status_code == 401
    assert 'expires_at>now()' in calls[0][0]
    assert calls[0][1] == (auth.digest('raw-session-token'),)


def test_hash_capacity_is_bounded():
    with auth.hash_capacity(), auth.hash_capacity():
        with pytest.raises(ApplicationError) as result:
            with auth.hash_capacity():
                raise AssertionError('Capacidade excedida não deve ser adquirida')
        assert result.value.status_code == 429


def test_password_hash_uses_argon2id_and_unique_salts():
    first, second = (
        auth.hasher.hash('a safe long passphrase'),
        auth.hasher.hash('a safe long passphrase'),
    )
    assert first.startswith('$argon2id$')
    assert first != second
    assert auth.hasher.verify(first, 'a safe long passphrase')


def test_schema_normalizes_email_and_rejects_naive_dates():
    user = Registration(
        name=' Pessoa ', email='PERSON@example.com', password='a safe long passphrase'
    )
    assert user.name == 'Pessoa'
    assert user.email == 'person@example.com'
    with pytest.raises(ValidationError):
        Filters(start=datetime(2026, 10, 20))


def test_query_scope_is_parameterized_and_always_authorized():
    filters = Filters(start=datetime(2026, 10, 1, tzinfo=UTC), classification='APROVADA')
    sql, params = queries.scope(UUID(int=1), filters)
    assert 'device_access' in sql and 'da.user_id=%s' in sql
    assert 'APROVADA' == params[-1]
    assert params[0] == UUID(int=1)


def test_adapter_preserves_null_and_converts_legacy_percentages():
    row = {
        'id': UUID(int=1),
        'dispositivo_id': None,
        'data_hora': datetime.now(UTC),
        'classificacao': 'APROVADA',
        'versao_algoritmo': None,
        'cor_media': 75,
        'regioes_anormais': None,
        'assimetria': 5,
        'circularidade': 0.8,
        'score_visual': None,
    }
    output = queries.adapt(row)
    assert output['metrics']['orange_color_ratio'] == 0.75
    assert output['metrics']['abnormal_region_ratio'] is None
    assert output['metrics']['visual_score'] is None
