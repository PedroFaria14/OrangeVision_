from web_api import migrate


def test_migration_command_defaults_to_plan_without_connecting(monkeypatch, capsys):
    monkeypatch.setattr('sys.argv', ['migrate'])
    monkeypatch.setattr(
        migrate.Settings,
        'load',
        lambda: (_ for _ in ()).throw(AssertionError('Plano não acessa o banco')),
    )
    migrate.main()
    assert 'Nenhuma execução' in capsys.readouterr().out


def test_explicit_migration_uses_versioned_transaction_without_startup_options(monkeypatch, capsys):
    calls = []

    class Database:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql, params=None, **kwargs):
            calls.append((sql, params, kwargs))
            return self

        def fetchone(self):
            return (True,)

    def connect(url, **kwargs):
        assert kwargs['autocommit'] is True
        assert 'options' not in kwargs
        return Database()

    monkeypatch.setattr('sys.argv', ['migrate', '--apply'])
    monkeypatch.setattr(
        migrate.Settings, 'load', lambda: type('Settings', (), {'database_url': 'test-only'})()
    )
    monkeypatch.setattr(migrate.psycopg, 'connect', connect)
    migrate.main()
    sql = calls[0][0]
    assert 'BEGIN;' in sql and sql.strip().endswith('COMMIT;')
    assert 'CREATE SCHEMA IF NOT EXISTS orangevision_web' in sql
    assert 'DROP TABLE' not in sql and 'DELETE FROM' not in sql
    assert len(calls) == 5
    assert '4/4' in capsys.readouterr().out
