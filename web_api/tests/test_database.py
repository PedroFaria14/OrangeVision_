from types import SimpleNamespace

import pytest

from web_api import database


class FakeConnection:
    def __init__(self):
        self.statements = []
        self.exit_error = None

    def __enter__(self):
        return self

    def __exit__(self, error_type, error, traceback):
        self.exit_error = error

    def execute(self, sql):
        self.statements.append(sql)


def test_pooler_connection_sets_transaction_timeout_without_startup_options(monkeypatch):
    db = FakeConnection()
    arguments = []

    def connect(url, **kwargs):
        arguments.append((url, kwargs))
        if 'options' in kwargs:
            raise AssertionError('O pooler não aceita options no startup.')
        return db

    monkeypatch.setattr(database.psycopg, 'connect', connect)
    settings = SimpleNamespace(database_url='postgresql://test-only@example.invalid/test')
    with database.connection(settings) as opened:
        assert opened is db
        assert db.statements == ['SET LOCAL statement_timeout = 10000']
        opened.execute('SELECT 1')
    assert arguments[0][1]['connect_timeout'] == 5
    assert arguments[0][1]['row_factory'] is database.dict_row
    assert db.statements[-1] == 'SELECT 1'


def test_database_errors_still_reach_the_connection_transaction(monkeypatch):
    db = FakeConnection()
    monkeypatch.setattr(database.psycopg, 'connect', lambda *args, **kwargs: db)
    failure = ValueError('test-only-failure')
    with pytest.raises(ValueError, match='test-only-failure'):
        with database.connection(SimpleNamespace(database_url='test-only')):
            raise failure
    assert db.exit_error is failure
