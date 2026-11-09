"""Worker Gemini embutido na Web API: sem banco, rede ou chamada real ao provedor."""
import threading
import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from web_api import gemini_worker
from web_api.config import Settings
from web_api.gemini_worker import FATAL, run_loop, start_in_process
from web_api.main import create_app

BASE = Settings('postgresql://fixture.invalid/db', ('https://example.test',), True, 3600)
READY = replace(BASE, gemini_enabled=True, gemini_api_key='fixture-key', gemini_inprocess=True)


def sequence(*statuses, calls=None):
    values = iter(statuses)

    def process(jobs, provider):
        if calls is not None:
            calls.append(1)
        return next(values, 'idle')

    return process


def test_flag_off_or_missing_key_never_starts_thread():
    assert start_in_process(BASE) is None
    assert start_in_process(replace(READY, gemini_inprocess=False)) is None
    assert start_in_process(replace(READY, gemini_api_key='')) is None
    assert start_in_process(replace(READY, gemini_enabled=False)) is None


def test_fatal_provider_status_stops_loop_without_raising():
    for status in FATAL:
        assert run_loop(READY, jobs=object(), provider=object(), process=sequence(status)) == status


def test_unexpected_error_is_logged_and_retried_instead_of_crashing():
    calls = []

    def process(jobs, provider):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError('transient')
        return 'provider_credentials'

    stop = threading.Event()
    original = stop.wait
    stop.wait = lambda seconds: original(0)
    assert run_loop(READY, stop, jobs=object(), provider=object(), process=process) == 'provider_credentials'
    assert len(calls) == 2


def test_once_returns_after_single_cycle():
    calls = []
    status = run_loop(
        READY, once=True, jobs=object(), provider=object(), process=sequence('completed', calls=calls)
    )
    assert status == 'completed'
    assert calls == [1]


def test_thread_processes_queue_and_stops_promptly():
    calls = []
    worker = start_in_process(
        READY, jobs=object(), provider=object(), process=sequence('completed', calls=calls)
    )
    assert worker is not None and worker.thread.daemon
    deadline = time.monotonic() + 2
    while len(calls) < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    started = time.monotonic()
    worker.stop(timeout=2)
    assert not worker.thread.is_alive()
    assert time.monotonic() - started < 1.5
    assert len(calls) >= 2


@pytest.mark.parametrize('settings', [BASE, READY])
def test_api_lifespan_starts_and_stops_worker_only_when_enabled(monkeypatch, settings):
    events = []

    class FakeWorker:
        def stop(self):
            events.append('stop')

    def fake_start(current):
        events.append('start' if current.gemini_inprocess else 'skip')
        return FakeWorker() if current.gemini_inprocess else None

    monkeypatch.setattr('web_api.main.start_in_process', fake_start)
    with TestClient(create_app(settings)) as client:
        assert client.get('/health').status_code == 200
    assert events == (['start', 'stop'] if settings.gemini_inprocess else ['skip'])


def test_inprocess_flag_is_validated(monkeypatch):
    monkeypatch.setenv('WEB_GEMINI_INPROCESS', 'talvez')
    with pytest.raises(RuntimeError, match='WEB_GEMINI_INPROCESS'):
        Settings.load()


def test_standalone_worker_still_requires_key(monkeypatch):
    monkeypatch.setattr(gemini_worker.Settings, 'load', classmethod(lambda cls: BASE))
    monkeypatch.setattr('sys.argv', ['gemini_worker', '--once'])
    with pytest.raises(SystemExit, match='GEMINI_API_KEY'):
        gemini_worker.main()
