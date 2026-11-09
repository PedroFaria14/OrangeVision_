"""Gemini sob demanda: a captura do Pi não pede Gemini e o local publica sozinho."""
from dataclasses import replace

import pytest

from web_api.config import Settings
from web_api.infrastructure.evaluation_repository import AutoAdoption

BASE = Settings('postgresql://fixture.invalid/db', ('https://example.test',), True, 3600)


def test_auto_request_defaults_to_true_and_is_validated(monkeypatch):
    monkeypatch.setenv('WEB_DATABASE_URL', 'postgresql://fixture.invalid/db')
    monkeypatch.delenv('WEB_GEMINI_AUTO_REQUEST', raising=False)
    assert Settings.load().gemini_auto_request is True
    monkeypatch.setenv('WEB_GEMINI_AUTO_REQUEST', 'false')
    assert Settings.load().gemini_auto_request is False
    monkeypatch.setenv('WEB_GEMINI_AUTO_REQUEST', 'talvez')
    with pytest.raises(RuntimeError, match='WEB_GEMINI_AUTO_REQUEST'):
        Settings.load()


def test_on_demand_gemini_never_runs_agreement_rule():
    settings = replace(BASE, gemini_auto_adopt=True, gemini_auto_request=False)
    # Sem tocar no banco: a regra de concordância fica desligada.
    assert AutoAdoption(settings).run('sample', 'user') == 'disabled'

