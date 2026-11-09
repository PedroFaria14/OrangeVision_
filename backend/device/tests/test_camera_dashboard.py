from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import cv2
import numpy as np
import pytest
from backend.device.api import ApiFailure, Offline
from backend.device.camera_dashboard import DashboardStatus, action_at, render_frame
from backend.device.camera_window import maintain_camera
from backend.device.samples import flush_camera_samples, process_one
from backend.device.storage import Store


@pytest.fixture
def store(tmp_path):
    result = Store(tmp_path / 'dashboard.db')
    result.initialize()
    return result


def test_pairing_and_network_are_not_the_same_status(store):
    device = str(uuid4())
    store.save_grant({
        'id': str(uuid4()), 'device_id': device, 'operator_name': 'Operador teste',
        'state': 'active', 'started_at': datetime.now(UTC).isoformat(),
        'authorization_expires_at': (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
    })
    status = DashboardStatus()
    status.refresh(store, device)
    assert status.session_valid
    assert 'Operador teste' in status.session
    assert 'nao significa online' in status.session_detail
    status.refresh(store, str(uuid4()))
    assert not status.session_valid


@pytest.mark.parametrize('validated', [False, True])
def test_quality_requires_validated_completed_result(validated):
    status = DashboardStatus()
    identity = str(uuid4())
    status.handle({'kind': 'result', 'sample_id': identity, 'result': {
        'state': 'completed', 'classification': 'APROVADA',
        'calibration_validated': validated, 'reason': 'Resultado experimental.',
    }})
    assert status.sample == identity
    assert ('Aprovada' in status.analysis) is validated
    if not validated:
        assert status.analysis == 'Qualidade nao avaliada.'


def test_upload_progress_is_separate_from_quality():
    status = DashboardStatus()
    status.handle({'kind': 'uploading'})
    assert 'Enviando' in status.upload
    assert status.analysis == 'Qualidade nao avaliada.'
    status.handle({'kind': 'synced', 'sample_id': str(uuid4())})
    assert 'Recebida pelo servidor' in status.upload
    assert status.analysis == 'Qualidade nao avaliada.'
    status.handle({'kind': 'upload_error', 'error': Offline('secret-details')})
    assert 'preservadas' in status.upload
    assert 'secret-details' not in status.upload
    status.handle({'kind': 'quarantined', 'status': 403})
    assert '403' in status.upload


def test_upload_attempt_is_not_blocked_by_failed_heartbeat(store, monkeypatch):
    grant = {'id': str(uuid4()), 'lease_token': 'test-only'}
    store.save_grant(grant)
    identity, remote_id = str(uuid4()), str(uuid4())
    store.save_camera_sample(identity, grant['id'], datetime.now(UTC).isoformat(), b'image')
    events = []

    def heartbeat(*args):
        raise ApiFailure(503)

    api = SimpleNamespace(
        heartbeat_samples=heartbeat,
        upload_camera_sample=lambda *a: {'id': remote_id, 'source_inspection_id': grant['id']},
        claim_sample=lambda _: None,
        sample_evaluations=lambda *a: {},
    )
    maintain_camera(store, api, None, None, events.append)
    assert [e['kind'] for e in events] == ['connection_error', 'uploading', 'synced']
    assert events[-1]['sample_id'] == remote_id
    assert store.camera_sample_counts() == {'synced': 1}


def test_rejected_upload_is_reported_and_preserved(store):
    grant = {'id': str(uuid4())}
    store.save_grant(grant)
    identity = str(uuid4())
    store.save_camera_sample(identity, grant['id'], datetime.now(UTC).isoformat(), b'image')

    def reject(*args):
        raise ApiFailure(403)

    events = []
    flush_camera_samples(store, SimpleNamespace(upload_camera_sample=reject), on_event=events.append)
    assert [e['kind'] for e in events] == ['uploading', 'quarantined']
    assert store.camera_sample_counts() == {'quarantined': 1}
    with store.db() as db:
        assert db.execute('SELECT image FROM camera_sample_outbox').fetchone()[0] == b'image'


def test_analysis_only_reports_result_after_server_acknowledgement(monkeypatch):
    from backend.device import samples

    monkeypatch.setattr(samples, 'retry', lambda operation: operation())
    monkeypatch.setattr(samples, 'sample_result', lambda *a, **k: {
        'state': 'completed', 'classification': 'APROVADA',
        'calibration_validated': True, 'reason': 'test-only',
    })
    identity = str(uuid4())
    events = []

    def finish(*args):
        assert [e['kind'] for e in events] == ['processing', 'result_pending']
        raise Offline('lost-ack')

    api = SimpleNamespace(
        claim_sample=lambda _: {'id': identity}, sample_image=lambda *a: b'image',
        finish_sample=finish,
    )
    with pytest.raises(Offline):
        process_one(api, on_event=events.append)
    assert [e['kind'] for e in events] == ['processing', 'result_pending']
    api.finish_sample = lambda *a: {'state': 'completed'}
    process_one(api, on_event=events.append)
    assert events[-1]['kind'] == 'result'
    assert events[-1]['result']['calibration_validated'] is True


def test_failed_poll_does_not_replace_previous_completed_result(store):
    events = []

    def claim(*args):
        raise ApiFailure(403)

    maintain_camera(store, SimpleNamespace(
        heartbeat_samples=lambda *a: None, claim_sample=claim,
    ), None, None, events.append)
    assert [e['kind'] for e in events] == ['connected', 'connection_error']
    status = DashboardStatus()
    status.analysis = 'Resultado anterior'
    for event in events:
        status.handle(event)
    assert status.analysis == 'Resultado anterior'


def test_dark_dashboard_render_and_button_geometry(monkeypatch):
    texts = []
    original = cv2.putText

    def record(image, text, *args, **kwargs):
        texts.append(text)
        return original(image, text, *args, **kwargs)

    monkeypatch.setattr(cv2, 'putText', record)
    from backend.device.camera_dashboard import _background
    _background.cache_clear()
    status = DashboardStatus()
    status.counts = {'pending': 3, 'quarantined': 1, 'synced': 2}
    image = render_frame(
        np.zeros((480, 640, 3), np.uint8),
        {'status': 'detected', 'box': [20, 20, 50, 50]},
        False, False, False, False, False, 'Teste', 'Aguardando', dashboard=status,
    )
    assert image.shape == (720, 960, 3)
    assert image[700, 950].max() < 50
    assert any('Fila: 3' in text for text in texts)
    assert 'Qualidade nao avaliada.' in texts
    assert action_at(840, 580, False) == 'mode'
    assert action_at(50, 530, False) is None
