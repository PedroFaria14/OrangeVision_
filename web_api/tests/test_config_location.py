"""Configuração da API fora da pasta do Raspberry, sem usar secrets locais nos testes."""

import pytest

from web_api import config


@pytest.fixture
def isolated_env(monkeypatch):
    for name in ('WEB_DATABASE_URL', 'DATABASE_URL', 'WEB_ALLOWED_ORIGINS', 'WEB_SESSION_SECONDS'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, 'load_dotenv', lambda *args, **kwargs: None)
    monkeypatch.setenv('WEB_SESSION_SECONDS', '28800')


def test_production_uses_render_environment_without_reading_device_env(isolated_env, monkeypatch):
    monkeypatch.setenv('WEB_ENV', 'production')
    monkeypatch.setenv('WEB_DATABASE_URL', 'postgresql://test-only:test-only@example.invalid/test')
    monkeypatch.setenv('WEB_ALLOWED_ORIGINS', 'https://frontend.example')
    monkeypatch.setattr(
        config, 'dotenv_values', lambda *args: pytest.fail('Produção não deve ler o env do Pi')
    )
    settings = config.Settings.load()
    assert settings.secure_cookie is True
    assert settings.origins == ('https://frontend.example',)


def test_production_without_database_does_not_fall_back_to_device(isolated_env, monkeypatch):
    monkeypatch.setenv('WEB_ENV', 'production')
    monkeypatch.setenv('WEB_ALLOWED_ORIGINS', 'https://frontend.example')
    monkeypatch.setattr(
        config, 'dotenv_values', lambda *args: pytest.fail('Produção não deve ler o env do Pi')
    )
    with pytest.raises(RuntimeError, match='Configure WEB_DATABASE_URL'):
        config.Settings.load()


def test_development_can_keep_existing_database_configuration(isolated_env, monkeypatch):
    monkeypatch.setenv('WEB_ENV', 'development')
    monkeypatch.setattr(config.Path, 'is_file', lambda path: True)
    observed = []

    def legacy_values(path):
        observed.append(path)
        return {'DATABASE_URL': 'postgresql://test-only:test-only@example.invalid/test'}

    monkeypatch.setattr(config, 'dotenv_values', legacy_values)
    settings = config.Settings.load()
    assert observed[0].parts[-2:] == ('backend', '.env')
    assert settings.secure_cookie is False


def test_web_database_has_priority_over_generic_database(isolated_env, monkeypatch):
    monkeypatch.setenv('WEB_ENV', 'development')
    monkeypatch.setenv('WEB_DATABASE_URL', 'postgresql://test-only:test-only@example.invalid/web')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://test-only:test-only@example.invalid/other')
    monkeypatch.setattr(
        config, 'dotenv_values', lambda *args: pytest.fail('Conexão explícita não precisa do Pi')
    )
    assert config.Settings.load().database_url.endswith('/web')
