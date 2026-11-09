import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from web_api.application.auth_service import digest
from web_api.application.device_service import DeviceService
from web_api.application.errors import ApplicationError
from web_api.config import Settings
from web_api.infrastructure.device_repository import DeviceRepository
from web_api.infrastructure.inspection_repository import InspectionRepository

URL = os.getenv('OV_DEVICE_TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not URL, reason='PostgreSQL descartável não configurado.')
MIGRATIONS = Path(__file__).parents[1] / 'migrations'
A, B = UUID(int=1), UUID(int=2)
LEGACY = UUID(int=99)


@pytest.fixture
def db():
    parsed = urlsplit(URL)
    assert parsed.hostname in ('127.0.0.1', 'localhost')
    assert parsed.path == '/orangevision_devices_test'
    with psycopg.connect(URL, autocommit=True, row_factory=dict_row) as connection:
        connection.execute('DROP SCHEMA IF EXISTS orangevision_web CASCADE')
        connection.execute('DROP TABLE IF EXISTS public.analises CASCADE')
        connection.execute('DROP TABLE IF EXISTS public.dispositivos CASCADE')
        connection.execute('CREATE TABLE public.dispositivos(id uuid PRIMARY KEY,nome varchar(100),status text,criado_em timestamptz)')
        connection.execute('CREATE TABLE public.analises(id uuid PRIMARY KEY,data_hora timestamptz)')
        for name in ['001_web_auth.sql', '002_inspection_sessions.sql']:
            connection.execute((MIGRATIONS / name).read_text(), prepare=False)
        for identity in [A, B]:
            connection.execute('INSERT INTO orangevision_web.users(id,name,email,password_hash) VALUES (%s,%s,%s,%s)',
                               (identity, 'Teste', f'{identity}@example.test', 'fixture-hash'))
        connection.execute("INSERT INTO public.dispositivos VALUES (%s,'Legado','offline',now())", (LEGACY,))
        connection.execute('INSERT INTO orangevision_web.device_access VALUES (%s,%s)', (A, LEGACY))
        yield connection


def enable(db):
    db.execute((MIGRATIONS / '006_device_registration.sql').read_text(), prepare=False)


def service(maximum=5):
    settings = Settings(URL, ('https://example.test',), True, 3600)
    return DeviceService(DeviceRepository(settings), maximum)


def test_missing_migration_preserves_legacy_list_and_blocks_creation(db):
    result = service().list_devices(A)
    assert result['registration_enabled'] is False
    assert result['items'][0]['id'] == LEGACY
    assert result['items'][0]['can_manage_credentials'] is False
    with pytest.raises(ApplicationError) as error:
        service().register(A, uuid4(), 'Pi')
    assert error.value.status_code == 503


def test_real_creation_replay_payload_conflict_and_legacy_ownership(db):
    enable(db)
    request = uuid4()
    result = service().register(A, request, 'Pi A')
    assert result.credential and result.device['can_manage_credentials']
    replay = service().register(A, request, 'Pi A')
    assert replay.device['id'] == result.device['id'] and replay.credential is None
    with pytest.raises(ApplicationError) as error:
        service().register(A, request, 'Outro nome')
    assert error.value.status_code == 409
    rows = service().list_devices(A)['items']
    assert len(rows) == 2
    assert next(item for item in rows if item['id'] == LEGACY)['can_manage_credentials'] is False
    assert service().list_devices(B)['items'] == []
    with pytest.raises(ApplicationError) as error:
        service().rotate(A, LEGACY, uuid4())
    assert error.value.status_code == 404
    stored = db.execute('SELECT token_hash FROM orangevision_web.device_credentials WHERE device_id=%s', (result.device['id'],)).fetchone()
    assert stored['token_hash'] == digest(result.credential)


def test_rotation_rejects_other_user_and_remains_compatible_with_pi_bearer(db):
    enable(db)
    result = service().register(A, uuid4(), 'Pi A')
    settings = Settings(URL, (), True, 3600)
    auth = InspectionRepository(settings)
    assert auth.authenticate_device(digest(result.credential))['device_id'] == result.device['id']
    with pytest.raises(ApplicationError) as error:
        service().rotate(B, result.device['id'], uuid4())
    assert error.value.status_code == 404
    request = uuid4()
    rotated = service().rotate(A, result.device['id'], request)
    assert auth.authenticate_device(digest(result.credential)) is None
    assert auth.authenticate_device(digest(rotated.credential))['device_id'] == result.device['id']
    assert service().rotate(A, result.device['id'], request).credential is None
    assert db.execute('SELECT count(*) AS count FROM orangevision_web.device_credentials WHERE device_id=%s', (result.device['id'],)).fetchone()['count'] == 2


def test_concurrent_same_request_creates_one_device_and_one_secret(db):
    enable(db)
    request = uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service().register(A, request, 'Pi A'), range(2)))
    assert results[0].device['id'] == results[1].device['id']
    assert sum(result.credential is not None for result in results) == 1
    assert db.execute('SELECT count(*) AS count FROM orangevision_web.managed_devices').fetchone()['count'] == 1


def test_quota_is_atomic_and_replays_still_work_at_limit(db):
    enable(db)
    def create(name):
        try:
            return service(1).register(A, uuid4(), name)
        except ApplicationError as error:
            return error
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, ['Pi A', 'Pi B']))
    assert sum(isinstance(result, ApplicationError) and result.status_code == 409 for result in results) == 1
    assert service(1).list_devices(A)['managed_count'] == 1


def test_request_ids_are_scoped_to_account(db):
    enable(db)
    request = uuid4()
    first = service().register(A, request, 'Pi A')
    second = service().register(B, request, 'Pi B')
    assert first.device['id'] != second.device['id']
    with pytest.raises(ApplicationError) as error:
        service().rotate(A, first.device['id'], request)
    assert error.value.status_code == 409


def test_rate_limit_is_persistent_and_does_not_block_replay(db):
    enable(db)
    request = uuid4()
    first = service().register(A, request, 'Pi A')
    for _ in range(9):
        service().rotate(A, first.device['id'], uuid4())
    with pytest.raises(ApplicationError) as error:
        service().rotate(A, first.device['id'], uuid4())
    assert error.value.status_code == 429
    assert error.value.headers == {'Retry-After': '900'}
    assert service().register(A, request, 'Pi A').credential is None


def test_revoked_access_does_not_allow_owner_to_rotate(db):
    enable(db)
    first = service().register(A, uuid4(), 'Pi A')
    db.execute('DELETE FROM orangevision_web.device_access WHERE user_id=%s AND device_id=%s', (A, first.device['id']))
    with pytest.raises(ApplicationError) as error:
        service().rotate(A, first.device['id'], uuid4())
    assert error.value.status_code == 404


def test_failed_credential_insert_rolls_back_device_access_quota_and_command(db):
    enable(db)
    first = service().register(A, uuid4(), 'Pi A')
    repository = service().store
    with pytest.raises(psycopg.errors.UniqueViolation):
        repository.issue(B, uuid4(), 'create', {'name': 'Não persistir'}, digest('fixture'), digest(first.credential), 5)
    assert service().list_devices(B)['items'] == []
    assert service().list_devices(B)['managed_count'] == 0
    assert db.execute("SELECT count(*) AS count FROM public.dispositivos WHERE nome='Não persistir'").fetchone()['count'] == 0
