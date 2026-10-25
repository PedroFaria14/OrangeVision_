import json
import sqlite3
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from backend.device.api import ApiFailure, Offline
from backend.device.locking import device_lock
from backend.device.storage import Store
from backend.device.sync import Synchronizer
from backend.device.worker import Worker


def test_resume_without_attempt_does_not_contact_api(setup):
    from backend.device.worker import PairingFailure

    store, device_id, old = setup
    store.deactivate(old['id'])
    with pytest.raises(PairingFailure, match='Nenhuma tentativa pendente'):
        Worker(device_id, store, object()).pair()
    assert store.pairing_attempt() is None


def test_different_pairing_code_cannot_replace_saved_activation(setup):
    from backend.device.worker import PairingFailure

    store, device_id, old = setup
    store.deactivate(old['id'])
    attempt = {
        'pairing_code': 'a' * 32,
        'activation_id': str(uuid4()),
        'lease_token': 'saved-secret',
    }
    store.pairing_attempt(attempt)
    with pytest.raises(PairingFailure, match='pair --resume') as error:
        Worker(device_id, store, object()).pair('b' * 32)
    assert store.pairing_attempt() == attempt
    assert 'saved-secret' not in str(error.value)
    assert attempt['pairing_code'] not in str(error.value)


def test_resume_closing_preserves_attempt_for_reconciliation(setup):
    from backend.device.worker import PairingFailure

    store, device_id, old = setup
    store.deactivate(old['id'])
    attempt = {
        'pairing_code': 'a' * 32,
        'activation_id': str(uuid4()),
        'lease_token': 'saved-secret',
    }
    store.pairing_attempt(attempt)

    class ClosingApi:
        def pair(self, received):
            assert received == attempt
            return {**old, 'state': 'closing'}

    with pytest.raises(PairingFailure, match='cancel-pairing'):
        Worker(device_id, store, ClosingApi()).pair()
    assert store.active_grant() is None
    assert store.pairing_attempt() == attempt


def test_late_upload_after_operator_change_and_restart_keeps_original_session(setup):
    worker = worker_for(setup)
    worker.api.fail = Offline('synthetic disconnected device')
    first_id = worker.capture(str(uuid4()))
    first_session = setup[2]['id']
    worker.store.deactivate(first_session)
    second = {
        **setup[2],
        'id': str(uuid4()),
        'operator_name': 'Pessoa B',
        'lease_token': 'second-test-lease',
    }
    worker.store.save_grant(second)
    # Novo Store/Worker simulam reinício sem descartar a outbox de A.
    restarted = Worker(worker.device_id, Store(worker.store.path), Api(second), Camera(), Vision())
    restarted.capture(str(uuid4()))
    # Cada lote de envio usa a autorização de uma única sessão.
    assert Synchronizer(restarted.store, restarted.api).once() == 1
    assert Synchronizer(restarted.store, restarted.api).once() == 1
    uploads = {item['id']: (grant, item) for grant, items in restarted.api.sent for item in items}
    assert uploads[first_id][0]['id'] == first_session
    assert uploads[first_id][1]['inspection_session_id'] == first_session
    assert uploads[first_id][0]['lease_token'] == setup[2]['lease_token']
    assert restarted.store.active_grant()['id'] == second['id']
    assert Synchronizer(restarted.store, restarted.api).once() == 0
    assert restarted.store.counts() == {'synced': 2}


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path / 'pipeline.db')
    store.initialize()
    device_id = str(uuid4())
    grant = {
        'id': str(uuid4()),
        'device_id': device_id,
        'operator_name': 'Pessoa A',
        'state': 'active',
        'started_at': (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        'observed_at': datetime.now(UTC).isoformat(),
        'authorization_expires_at': (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        'lease_token': 'test-only-lease-token-000000000000000',
    }
    store.save_grant(grant)
    return store, device_id, grant


class Api:
    def __init__(self, grant):
        self.grant = grant
        self.fail = None
        self.sent = []

    def status(self, grant):
        if self.fail:
            raise self.fail
        return self.grant

    def ingest(self, grant, items):
        if self.fail:
            raise self.fail
        self.sent.append((grant, items))
        return {'items': [{'id': item['id'], 'status': 'accepted'} for item in items]}


class Camera:
    def __init__(self):
        self.calls = 0

    def capture(self):
        self.calls += 1
        return object()


class Vision:
    def analyze(self, frame):
        return {
            'classification': 'APROVADA',
            'metrics': {
                'orange_color_ratio': 0.8,
                'abnormal_region_ratio': 0.02,
                'circularity': 0.9,
                'asymmetry': 0.03,
                'visual_score': 85.0,
            },
            'calibration_version': 'test-only-v1',
            'algorithm_version': 'test-only',
            'reason': 'Synthetic fixture only.',
        }


def worker_for(setup, vision=None):
    store, device_id, grant = setup
    api, camera = Api(grant), Camera()
    return Worker(device_id, store, api, camera, vision or Vision())


def test_capture_is_persisted_with_outbox_and_repeated_command_does_not_reopen_camera(setup):
    worker = worker_for(setup)
    command = str(uuid4())
    first = worker.capture(command)
    assert worker.capture(command) == first
    assert worker.camera.calls == 1
    assert worker.store.job(command)['state'] == 'completed'
    assert worker.store.counts() == {'pending': 1}


def test_vision_adapter_cannot_override_frozen_session_or_identifier(setup):
    class UntrustedVision(Vision):
        def analyze(self, frame):
            return {
                **super().analyze(frame),
                'inspection_session_id': str(uuid4()),
                'id': 'wrong',
                'timestamp': 'wrong',
            }

    worker = worker_for(setup, UntrustedVision())
    analysis_id = worker.capture(str(uuid4()))
    payload = json.loads(worker.store.due(float('inf'))[0]['payload'])
    assert payload['inspection_session_id'] == setup[2]['id']
    assert payload['id'] == analysis_id
    assert payload['timestamp'] != 'wrong'


def test_authorized_offline_capture_preserves_owner_for_late_sync(setup):
    worker = worker_for(setup)
    worker.api.fail = Offline('test-only')
    worker.capture(str(uuid4()))
    assert worker.store.counts() == {'pending': 1}
    other = {**setup[2], 'id': str(uuid4()), 'operator_name': 'Pessoa B'}
    worker.store.save_grant(other)
    worker.api.fail = None
    assert Synchronizer(worker.store, worker.api).once() == 1
    grant, items = worker.api.sent[0]
    assert grant['id'] == setup[2]['id']
    assert items[0]['inspection_session_id'] == setup[2]['id']


def test_expired_or_denied_authorization_blocks_capture(setup):
    worker = worker_for(setup)
    worker.api.fail = ApiFailure(403)
    with pytest.raises(ApiFailure):
        worker.capture(str(uuid4()))
    assert worker.camera.calls == 0
    expired = {
        **setup[2],
        'authorization_expires_at': (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
    }
    worker.store.save_grant(expired)
    with pytest.raises(RuntimeError):
        worker.capture(str(uuid4()))
    assert worker.camera.calls == 0


def test_segmentation_failure_never_produces_revisar_or_outbox(setup):
    class FailingVision:
        def analyze(self, frame):
            raise ValueError('segmentation failed')

    worker = worker_for(setup, FailingVision())
    command = str(uuid4())
    with pytest.raises(ValueError):
        worker.capture(command)
    assert worker.store.job(command)['state'] == 'failed'
    assert worker.store.counts() == {}


def test_failure_of_outbox_insert_rolls_back_analysis_and_completion(setup):
    worker = worker_for(setup)
    with worker.store.db() as db:
        db.execute(
            "CREATE TRIGGER fail_outbox BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT,'test-only disk failure'); END"
        )
    command = str(uuid4())
    with pytest.raises(sqlite3.IntegrityError):
        worker.capture(command)
    with worker.store.db() as db:
        assert db.execute('SELECT count(*) FROM captured_analyses').fetchone()[0] == 0
    assert worker.store.job(command)['state'] == 'failed'


def test_recovery_marks_unknown_work_and_does_not_repeat_physical_action(setup):
    store, _, grant = setup
    command = str(uuid4())
    store.reserve(command, grant['id'])
    store.recover_interrupted()
    worker = worker_for(setup)
    with pytest.raises(RuntimeError):
        worker.capture(command)
    assert worker.camera.calls == 0
    assert store.job(command)['state'] == 'interrupted'


def test_shared_camera_and_operator_change_are_excluded_while_busy(setup):
    worker = worker_for(setup)
    worker.busy.acquire()
    try:
        with pytest.raises(RuntimeError):
            worker.capture(str(uuid4()))
        with pytest.raises(RuntimeError):
            worker.pair('test-only-code')
        with pytest.raises(RuntimeError):
            worker.close_inspection()
    finally:
        worker.busy.release()
    assert worker.camera.calls == 0


def test_process_lock_excludes_a_second_worker(tmp_path):
    path = tmp_path / 'worker.lock'
    with device_lock(path):
        with pytest.raises(RuntimeError):
            with device_lock(path):
                raise AssertionError('second owner')


def test_missing_ack_stays_pending_and_conflict_is_retained_in_quarantine(setup):
    worker = worker_for(setup)
    analysis_id = worker.capture(str(uuid4()))
    worker.api.ingest = lambda grant, items: {'items': []}
    sync = Synchronizer(worker.store, worker.api, clock=lambda: 1000)
    assert sync.once() == 0
    assert worker.store.counts() == {'pending': 1}
    worker.api.ingest = lambda grant, items: {'items': [{'id': analysis_id, 'status': 'conflict'}]}
    assert Synchronizer(worker.store, worker.api, clock=lambda: 2000).once() == 0
    assert worker.store.counts() == {'quarantined': 1}


def test_retry_after_is_observed_and_lost_ack_duplicate_is_confirmed(setup):
    worker = worker_for(setup)
    analysis_id = worker.capture(str(uuid4()))
    worker.api.fail = ApiFailure(429, retry_after=900)
    assert Synchronizer(worker.store, worker.api, clock=lambda: 1000).once() == 0
    assert worker.store.due(1899) == []
    assert len(worker.store.due(1901)) == 1
    worker.api.fail = None
    worker.api.ingest = lambda grant, items: {'items': [{'id': analysis_id, 'status': 'duplicate'}]}
    assert Synchronizer(worker.store, worker.api, clock=lambda: 2000).once() == 1
    assert worker.store.counts() == {'synced': 1}


def test_pipeline_refuses_to_modify_legacy_sqlite(tmp_path):
    import sqlite3

    path = tmp_path / 'legacy.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE analises(id TEXT)')
    with pytest.raises(RuntimeError):
        Store(path).initialize()
    with sqlite3.connect(path) as db:
        assert (
            db.execute("SELECT count(*) FROM sqlite_master WHERE name='capture_jobs'").fetchone()[0]
            == 0
        )


def test_pairing_lost_response_reuses_persisted_activation_and_lease(setup):
    store, device_id, old = setup
    store.deactivate(old['id'])
    new = {**old, 'id': str(uuid4())}
    seen = []

    class PairApi:
        def pair(self, attempt):
            seen.append(dict(attempt))
            if len(seen) == 1:
                raise Offline('ACK lost after simulated activation')
            return new

    worker = Worker(device_id, store, PairApi())
    with pytest.raises(Offline):
        worker.pair('c' * 32)
    assert store.pairing_attempt() is not None
    # Simula reinício: a recuperação usa o código/activation/lease persistidos,
    # mesmo se o navegador já perdeu a apresentação do código.
    worker = Worker(device_id, Store(store.path), PairApi())
    result = worker.pair()
    assert seen[0] == seen[1]
    assert result['id'] == new['id']
    assert 'lease_token' not in result
    assert store.active_grant()['lease_token'] == seen[0]['lease_token']
    assert store.pairing_attempt() is None


def test_two_workers_cannot_open_camera_concurrently_through_same_store(setup):
    from threading import Event, Thread

    entered, release = Event(), Event()
    first = worker_for(setup)
    second = worker_for(setup)
    results = []

    class BlockingCamera:
        def capture(self):
            entered.set()
            assert release.wait(5)
            return object()

    first.camera = BlockingCamera()

    def capture():
        results.append(first.capture(str(uuid4())))

    thread = Thread(target=capture)
    thread.start()
    try:
        assert entered.wait(5)
        with pytest.raises(sqlite3.IntegrityError):
            second.capture(str(uuid4()))
        assert second.camera.calls == 0
    finally:
        release.set()
        thread.join(5)
    assert len(results) == 1
    assert first.store.counts() == {'pending': 1}


def test_observed_closing_never_falls_back_to_offline_capture_when_ack_fails(setup):
    worker = worker_for(setup)
    worker.api.grant = {**setup[2], 'state': 'closing'}

    def failed_ack(grant):
        raise Offline('test-only outage during close ACK')

    worker.api.closed = failed_ack
    with pytest.raises(RuntimeError, match='Encerramento observado'):
        worker.capture(str(uuid4()))
    assert worker.camera.calls == 0
    assert worker.store.counts() == {}
    worker.api.fail = Offline('test-only outage after observing closure')
    with pytest.raises(RuntimeError):
        worker.capture(str(uuid4()))
    assert worker.camera.calls == 0


def test_definitive_denial_is_persisted_and_cannot_be_bypassed_by_later_offline_mode(setup):
    worker = worker_for(setup)
    worker.api.fail = ApiFailure(401)
    with pytest.raises(ApiFailure):
        worker.capture(str(uuid4()))
    assert worker.store.active_grant()['state'] == 'blocked'
    worker.api.fail = Offline('test-only')
    with pytest.raises(RuntimeError):
        worker.capture(str(uuid4()))
    assert worker.camera.calls == 0
    worker.api.fail = None
    assert worker.capture(str(uuid4()))
    assert worker.store.active_grant()['state'] == 'active'


def test_late_sync_error_does_not_regress_an_already_acknowledged_item(setup):
    worker = worker_for(setup)
    analysis_id = worker.capture(str(uuid4()))
    old = worker.store.due(1000)[0]
    assert Synchronizer(worker.store, worker.api, clock=lambda: 1000).once() == 1
    worker.store.mark(analysis_id, 'quarantined', 'LateFailureFromAnotherSender')
    worker.store.retry(old, 1000, 30, 'LateMissingAck')
    assert worker.store.counts() == {'synced': 1}


def test_clock_before_authorized_start_blocks_offline_capture(setup):
    worker = worker_for(setup)
    grant = {
        **setup[2],
        'started_at': (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        'authorization_expires_at': (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
    }
    worker.store.save_grant(grant)
    worker.api.fail = Offline('test-only')
    with pytest.raises(RuntimeError, match='Relógio local'):
        worker.capture(str(uuid4()))
    assert worker.camera.calls == 0


def test_camera_cleanup_attempts_close_even_when_csi_stop_fails():
    from types import SimpleNamespace

    from backend.device.camera import Camera as CameraAdapter

    calls = []

    class Csi:
        def stop(self):
            calls.append('stop')
            raise RuntimeError('synthetic driver failure')

        def close(self):
            calls.append('close')

    adapter = CameraAdapter(SimpleNamespace(width=100, height=100, camera_adapter='csi'))
    adapter.camera = Csi()
    with pytest.raises(RuntimeError):
        adapter.close()
    assert calls == ['stop', 'close']
    assert adapter.camera is None


def test_fresh_server_clock_mismatch_blocks_capture_before_camera_access(setup):
    worker = worker_for(setup)
    worker.api.grant = {
        **setup[2],
        'observed_at': (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
    }
    with pytest.raises(RuntimeError, match='UTC/NTP'):
        worker.capture(str(uuid4()))
    assert worker.camera.calls == 0
    assert worker.store.counts() == {}
