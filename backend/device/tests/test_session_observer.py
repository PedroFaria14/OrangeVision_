"""A janela confirma sozinha o encerramento pedido no site (sem esperar captura)."""
from types import SimpleNamespace

from backend.device import camera_window
from backend.device.camera_window import observe_session


class Store:
    def __init__(self, grant):
        self.grant = grant

    def active_grant(self):
        return self.grant


def worker(error=None):
    calls = []

    def capture_grant(grant):
        calls.append(grant)
        if error:
            raise error
        return grant

    return SimpleNamespace(_capture_grant=capture_grant, calls=calls)


def reset():
    camera_window._last_session_check['at'] = -float('inf')


def test_closing_requested_on_site_is_confirmed_by_the_loop():
    reset()
    w = worker(RuntimeError('Sessão encerrada; captura bloqueada.'))
    assert observe_session(Store({'id': 's1'}), w, now=100) == 'closed'
    assert len(w.calls) == 1


def test_active_session_is_checked_at_most_every_interval():
    reset()
    w = worker()
    assert observe_session(Store({'id': 's1'}), w, now=100) == 'active'
    assert observe_session(Store({'id': 's1'}), w, now=105) is None
    assert observe_session(Store({'id': 's1'}), w, now=116) == 'active'
    assert len(w.calls) == 2


def test_no_session_or_no_worker_does_nothing():
    reset()
    assert observe_session(Store(None), worker(), now=100) is None
    reset()
    assert observe_session(Store({'id': 's1'}), None, now=100) is None


def test_other_failures_are_reported_and_retried_later():
    reset()
    w = worker(RuntimeError('Encerramento observado; confirmação pendente, sem nova captura.'))
    assert observe_session(Store({'id': 's1'}), w, now=100) == 'error'
