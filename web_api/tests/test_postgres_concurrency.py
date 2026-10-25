"""Integração opt-in: banco dedicado *_test, conexões independentes e schemas descartáveis.

Não lê .env nem usa Settings.load(). Nunca utiliza automaticamente o banco da API.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Barrier, Lock
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from web_api.application.errors import ApplicationError
from web_api.infrastructure import inspection_repository as module


@pytest.fixture
def postgres_inspections(monkeypatch):
    dsn = os.environ.get('ORANGEVISION_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Exige ORANGEVISION_TEST_DATABASE_URL apontando para banco dedicado *_test.')
    if not conninfo_to_dict(dsn).get('dbname', '').endswith('_test'):
        pytest.fail('Integração aceita somente banco dedicado com nome terminado em _test.')
    marker = 'ov_test_' + uuid4().hex
    web, public = marker + '_w', marker + '_p'
    control = SimpleNamespace(barrier=None, rollback=False, pids=set())
    lock = Lock()

    def rewrite(statement):
        return statement.replace('orangevision_web', web).replace('public.', public + '.')

    @contextmanager
    def connection(_settings):
        with psycopg.connect(dsn, connect_timeout=5, row_factory=dict_row) as db:
            db.execute("SET LOCAL statement_timeout = '10s'")
            db.execute("SET LOCAL lock_timeout = '5s'")
            with lock:
                control.pids.add(db.info.backend_pid)
            if control.barrier:
                control.barrier.wait(timeout=10)

            class Proxy:
                def execute(self, statement, params=None):
                    return db.execute(rewrite(statement), params)

            yield Proxy()
            if control.rollback:
                raise RuntimeError('synthetic failure before commit')

    with psycopg.connect(dsn, connect_timeout=5, autocommit=True, row_factory=dict_row) as admin:
        try:
            admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(public)))
            admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(web)))
            admin.execute(
                sql.SQL('CREATE TABLE {}.dispositivos (id uuid PRIMARY KEY)').format(
                    sql.Identifier(public)
                )
            )
            admin.execute(
                sql.SQL(
                    'CREATE TABLE {}.analises (id uuid PRIMARY KEY, data_hora timestamptz)'
                ).format(sql.Identifier(public))
            )
            # Executa o DDL real redirecionado exclusivamente aos schemas deste teste.
            for filename in ('001_web_auth.sql', '002_inspection_sessions.sql'):
                script = (Path(module.__file__).parents[1] / 'migrations' / filename).read_text(
                    encoding='utf-8'
                )
                admin.execute(rewrite(script), prepare=False)
            users = [uuid4(), uuid4()]
            device = uuid4()
            admin.execute(rewrite('INSERT INTO public.dispositivos VALUES (%s)'), (device,))
            for identity in users:
                admin.execute(
                    rewrite(
                        'INSERT INTO orangevision_web.users(id,name,email,password_hash) VALUES (%s,%s,%s,%s)'
                    ),
                    (
                        identity,
                        'Test operator',
                        str(identity) + '@example.com',
                        'test-only-not-for-login',
                    ),
                )
                admin.execute(
                    rewrite('INSERT INTO orangevision_web.device_access VALUES (%s,%s)'),
                    (identity, device),
                )
            monkeypatch.setattr(module, 'connection', connection)
            yield module.InspectionRepository(None), users, device, control, admin, rewrite
        finally:
            # Somente namespaces aleatórios criados pela própria fixture.
            if admin.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
                admin.execute('ROLLBACK')
            admin.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(web)))
            admin.execute(
                sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(public))
            )


def test_postgres_two_users_cannot_open_same_device(postgres_inspections):
    repository, users, device, control, admin, rewrite = postgres_inspections
    control.barrier = Barrier(2)

    def start(identity):
        try:
            return repository.start(identity, device, uuid4(), uuid4().hex)
        except ApplicationError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(start, users))
    assert len(control.pids) == 2
    assert sum(isinstance(result, dict) for result in outcomes) == 1
    assert sum(isinstance(result, ApplicationError) for result in outcomes) == 1
    assert (
        next(result for result in outcomes if isinstance(result, ApplicationError)).status_code
        == 409
    )
    assert (
        admin.execute(
            rewrite('SELECT count(*) AS count FROM orangevision_web.inspection_sessions')
        ).fetchone()['count']
        == 1
    )


def test_postgres_failed_commit_rolls_back_session(postgres_inspections):
    repository, users, device, control, admin, rewrite = postgres_inspections
    control.rollback = True
    request = uuid4()
    with pytest.raises(RuntimeError, match='synthetic failure before commit'):
        repository.start(users[0], device, request, 'test-hash')
    assert (
        admin.execute(
            rewrite('SELECT count(*) AS count FROM orangevision_web.inspection_sessions')
        ).fetchone()['count']
        == 0
    )
    control.rollback = False
    assert repository.start(users[0], device, request, 'test-hash')['state'] == 'pending'


def test_postgres_lost_pair_reply_reuses_activation_without_changing_owner(postgres_inspections):
    repository, users, device, _, admin, rewrite = postgres_inspections
    request, activation = uuid4(), uuid4()
    started = repository.start(users[0], device, request, 'test-pair-hash')
    assert repository.start(users[0], device, request, 'test-pair-hash')['id'] == started['id']
    # Primeira resposta é descartada, depois a mesma ativação é reenviada.
    repository.pair(device, 'test-pair-hash', activation, 'test-lease-hash', 900)
    recovered = repository.pair(device, 'test-pair-hash', activation, 'test-lease-hash', 900)
    assert recovered['id'] == started['id']
    assert recovered['user_id'] == users[0]
    assert (
        admin.execute(
            rewrite('SELECT count(*) AS count FROM orangevision_web.inspection_sessions')
        ).fetchone()['count']
        == 1
    )
