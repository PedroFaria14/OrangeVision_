import json
import stat
from types import SimpleNamespace
from uuid import uuid4

import cv2
import numpy as np
import pytest
from backend.device import samples
from backend.device.api import ApiFailure, Offline
from backend.device.camera_dashboard import DashboardStatus, action_at, render_frame
from backend.device.camera_window import maintain_camera
from backend.device.sample_status import analysis_identity
from backend.device.storage import Store

LOCAL_RESULT = {
    'state': 'completed', 'classification': 'APROVADA',
    'reason': 'Classificacao sintetica de teste.', 'calibration_validated': True,
    'calibration_version': 'test-only', 'algorithm_version': 'test-only',
    'mask_base64': 'private-mask-test',
}


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(samples, 'retry', lambda operation: operation())
    monkeypatch.setattr(samples, 'sample_result', lambda *a, **k: dict(LOCAL_RESULT))
    result = Store(tmp_path / 'samples.db')
    result.initialize()
    return result


class Api:
    def __init__(self, *, response=None, sample_id=None):
        self.sample_id = sample_id or str(uuid4())
        self.analysis_id = str(uuid4())
        self.response = response
        self.claims, self.finishes, self.downloads = [], [], []

    def claim_sample(self, attempt):
        self.claims.append(dict(attempt))
        return {'id': self.sample_id}

    def heartbeat_samples(self, *args):
        return {}

    def sample_image(self, identity, lease):
        self.downloads.append((identity, lease))
        return b'synthetic-image'

    def finish_sample(self, identity, lease, payload):
        self.finishes.append((identity, lease, json.loads(json.dumps(payload))))
        return self.response if self.response is not None else {
            'state': 'completed', 'analysis_id': self.analysis_id,
        }

    def ingest(self, *args):
        pytest.fail('Nao pode criar um segundo envio de analise.')


def test_analysis_id_is_persisted_and_restored_separately_from_upload(store):
    api = Api()
    events = []
    result = samples.process_one(api, store=store, on_event=events.append)
    assert result['analysis_id'] == api.analysis_id
    assert [e['kind'] for e in events] == ['processing', 'result_pending', 'result']
    assert events[-1]['analysis_id'] == api.analysis_id
    record = Store(store.path).latest_sample_status()
    assert record['confirmation'] == 'confirmed'
    assert record['analysis_id'] == api.analysis_id
    assert record['result']['classification'] == 'APROVADA'
    public = json.dumps(record)
    assert 'lease_token' not in public and 'claim_id' not in public
    assert 'private-mask-test' not in public
    assert api.claims[0]['lease_token'] not in public
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    with store.db() as db:
        row = db.execute('SELECT payload,lease_token,claim_id FROM sample_status').fetchone()
        assert tuple(row) == (None, None, None)
    restored = DashboardStatus()
    restored.restore(Store(store.path))
    assert 'Aprovada' in restored.analysis
    assert restored.analysis_id == api.analysis_id
    assert restored.registration == 'Registrada no historico.'
    assert 'periodo' in restored.registration_detail
    assert len(api.claims) == len(api.downloads) == len(api.finishes) == 1


@pytest.mark.parametrize('remote_id', [None, ''])
def test_http_success_without_analysis_id_never_confirms_graph_registration(store, remote_id):
    api = Api(response={'state': 'completed', 'analysis_id': remote_id})
    samples.process_one(api, store=store)
    restored = DashboardStatus()
    restored.restore(Store(store.path))
    assert 'Aprovada' in restored.analysis
    assert restored.analysis_id is None
    assert restored.registration_tone != 'green'
    assert 'nao confirmou' in restored.registration
    assert store.pending_sample_work() is None  # ACK válido, não publicar outra análise.


def test_absent_analysis_id_is_backward_compatible_but_not_registration(store):
    samples.process_one(Api(response={'state': 'awaiting_review'}), store=store)
    record = store.latest_sample_status()
    assert record['analysis_id'] is None and record['confirmation'] == 'confirmed'
    restored = DashboardStatus()
    restored.restore(store)
    assert restored.analysis == 'Qualidade nao avaliada.'
    assert restored.registration_tone != 'green'


@pytest.mark.parametrize('bad_id', ['invalid', 123, True, '00000000-0000-0000-0000-000000000000'])
def test_invalid_analysis_id_keeps_result_pending_instead_of_claiming_registration(store, bad_id):
    api = Api(response={'state': 'completed', 'analysis_id': bad_id})
    events = []
    with pytest.raises(RuntimeError, match='analysis_id'):
        samples.process_one(api, store=store, on_event=events.append)
    assert events[-1]['kind'] == 'result_pending'
    record = store.pending_sample_work()
    assert record['payload']['classification'] == 'APROVADA'
    assert record['analysis_id'] is None
    restored = DashboardStatus()
    restored.restore(store)
    assert '(local)' in restored.analysis
    assert restored.registration_tone == 'orange'


def test_lost_finish_response_resumes_exact_payload_after_restart_without_new_claim(store, monkeypatch):
    api = Api()
    original_finish = api.finish_sample

    def lost(*args):
        original_finish(*args)  # Simula operação aceita e resposta perdida.
        raise Offline('private-lost-reply')

    api.finish_sample = lost
    with pytest.raises(Offline):
        samples.process_one(api, store=store)
    before = store.pending_sample_work()
    assert before['confirmation'] == 'pending'
    restarted = Store(store.path)
    status = DashboardStatus()
    status.restore(restarted)
    assert status.registration_tone != 'green'
    assert 'pendente' in status.registration
    status.handle({'kind': 'analysis_error', 'sample_id': api.sample_id, 'error': Offline('private')})
    assert 'Aprovada' in status.analysis and '(local)' in status.analysis
    assert status.analysis_detail == LOCAL_RESULT['reason']
    assert 'pode ter recebido' in status.registration_detail

    monkeypatch.setattr(samples, 'sample_result', lambda *a, **k: pytest.fail('Nao recalcular resultado pendente.'))
    api.finish_sample = original_finish
    samples.process_one(api, store=restarted)
    assert len(api.claims) == len(api.downloads) == 1
    assert len(api.finishes) == 2
    assert api.finishes[0] == api.finishes[1]
    assert restarted.latest_sample_status()['analysis_id'] == api.analysis_id
    assert restarted.pending_sample_work() is None


def test_lost_claim_response_reuses_persisted_attempt_after_restart(store):
    api = Api()
    original_claim = api.claim_sample

    def lost(attempt):
        original_claim(attempt)
        raise Offline('lost-claim')

    api.claim_sample = lost
    with pytest.raises(Offline):
        samples.process_one(api, store=store)
    assert store.sample_claim() == api.claims[0]
    api.claim_sample = original_claim
    samples.process_one(api, store=Store(store.path))
    assert api.claims[0] == api.claims[1]
    assert store.sample_claim() is None
    assert len(api.finishes) == 1


def test_image_failure_keeps_original_job_for_restart(store):
    api = Api()
    original_download = api.sample_image

    def lost(*args):
        raise Offline('download-failed')

    api.sample_image = lost
    with pytest.raises(Offline):
        samples.process_one(api, store=store)
    assert store.pending_sample_work()['confirmation'] == 'processing'
    status = DashboardStatus()
    status.restore(Store(store.path))
    assert status.sample == api.sample_id
    assert status.analysis == 'Em analise...'
    assert status.registration_tone != 'green'
    api.sample_image = original_download
    samples.process_one(api, store=Store(store.path))
    assert len(api.claims) == len(api.finishes) == 1


def test_rejected_lease_keeps_uncertainty_and_never_creates_another_analysis(store):
    api = Api()

    def rejected(*args):
        raise ApiFailure(409)

    api.finish_sample = rejected
    for _ in range(2):
        with pytest.raises(ApiFailure):
            samples.process_one(api, store=store)
    assert len(api.claims) == len(api.downloads) == 1
    assert store.pending_sample_work()['payload']['classification'] == 'APROVADA'


def test_server_category_and_reason_are_displayed_without_conflating_registration(store):
    api = Api(response={
        'state': 'completed', 'classification': 'REVISAR', 'reason': 'Defeito visual confirmado.',
        'calibration_validated': True, 'analysis_id': str(uuid4()),
    })
    samples.process_one(api, store=store)
    status = DashboardStatus()
    status.restore(store)
    assert status.analysis == 'Revisar a fruta'
    assert status.analysis_detail == 'Defeito visual confirmado.'
    assert status.registration_tone == 'green'


def test_registered_analysis_does_not_invent_quality_without_calibration(store, monkeypatch):
    monkeypatch.setattr(samples, 'sample_result', lambda *a, **k: {
        'state': 'awaiting_review', 'classification': None,
        'reason': 'Sem classificacao: calibracao ausente.', 'calibration_validated': False,
    })
    api = Api(response={'state': 'awaiting_review', 'analysis_id': str(uuid4())})
    samples.process_one(api, store=store)
    status = DashboardStatus()
    status.restore(store)
    assert status.analysis == 'Qualidade nao avaliada.'
    assert 'calibracao ausente' in status.analysis_detail
    assert status.registration_tone == 'green'  # Registro e qualidade são independentes.


def test_upload_receipt_keeps_analysis_id_across_processing_ack_without_id(store):
    grant = {'id': str(uuid4())}
    photo_id, sample_id, analysis_id = str(uuid4()), str(uuid4()), str(uuid4())
    store.save_grant(grant)
    store.save_camera_sample(photo_id, grant['id'], 'stamp', b'original-photo')
    upload = SimpleNamespace(upload_camera_sample=lambda *a: {
        'id': sample_id, 'source_inspection_id': grant['id'], 'analysis_id': analysis_id,
    })
    samples.flush_camera_samples(store, upload)
    assert store.camera_sample_counts() == {'synced': 1}
    api = Api(response={'state': 'completed'}, sample_id=sample_id)
    result = samples.process_one(api, store=store)
    assert result['analysis_id'] == analysis_id
    assert store.latest_sample_status()['analysis_id'] == analysis_id
    assert store.latest_sample_status(receipt=True)['photo_id'] == photo_id


def test_mismatching_analysis_id_never_overwrites_known_registration(store):
    grant = {'id': str(uuid4())}
    photo_id, sample_id, known = str(uuid4()), str(uuid4()), str(uuid4())
    store.save_grant(grant)
    store.save_camera_sample(photo_id, grant['id'], 'stamp', b'photo')
    store.record_sample_receipt(photo_id, sample_id, known)
    api = Api(sample_id=sample_id)
    with pytest.raises(RuntimeError, match='outro analysis_id'):
        samples.process_one(api, store=store)
    assert store.latest_sample_status()['analysis_id'] == known
    assert store.pending_sample_work() is not None


def test_new_schema_preserves_existing_photo_queue(store):
    grant = {'id': str(uuid4())}
    store.save_grant(grant)
    photo_id = str(uuid4())
    store.save_camera_sample(photo_id, grant['id'], 'stamp', b'preserve-exact-bytes')
    with store.db() as db:
        db.execute('DROP TABLE sample_status')
        db.execute('DROP TABLE sample_claim_attempt')
    store.initialize()
    assert store.pending_camera_samples()[0]['image'] == b'preserve-exact-bytes'
    assert store.active_grant() == grant
    assert store.latest_sample_status() is None


def test_details_overlay_shows_full_reason_and_registration_ids(store, monkeypatch):
    api = Api(response={
        'state': 'completed', 'analysis_id': str(uuid4()),
        'reason': 'Motivo completo: contorno conferido e resultado registrado.',
    })
    samples.process_one(api, store=store)
    status = DashboardStatus()
    status.restore(store)
    texts = []
    original = cv2.putText

    def record(image, text, *args, **kwargs):
        texts.append(text)
        return original(image, text, *args, **kwargs)

    monkeypatch.setattr(cv2, 'putText', record)
    image = render_frame(
        np.zeros((480, 640, 3), np.uint8), {'status': 'not_detected'},
        False, False, False, False, False, 'Teste', 'Teste', dashboard=status, details=True,
    )
    assert image.shape == (720, 960, 3)
    assert any(api.sample_id in text for text in texts)
    assert any(api.response['analysis_id'] in text for text in texts)
    assert any('Motivo completo:' in text for text in texts)
    assert action_at(300, 580, False) == 'details'


@pytest.mark.parametrize('value', [None, ''])
def test_empty_analysis_id_is_not_registration(value):
    assert analysis_identity(value) is None


def test_long_reason_can_be_read_to_the_end_with_detail_pages(monkeypatch):
    from backend.device.camera_dashboard import _wrapped

    status = DashboardStatus()
    status.analysis_detail = 'Motivo detalhado para conferir a amostra. ' * 50 + 'FIM DO MOTIVO.'
    pages = (len(_wrapped(status.analysis_detail, 602, 0.42)) + 6) // 7
    assert pages > 1
    texts = []
    original = cv2.putText

    def record(image, text, *args, **kwargs):
        texts.append(text)
        return original(image, text, *args, **kwargs)

    monkeypatch.setattr(cv2, 'putText', record)
    render_frame(
        np.zeros((480, 640, 3), np.uint8), {'status': 'not_detected'},
        False, False, False, False, False, '', '', dashboard=status,
        details=True, details_page=pages - 1,
    )
    assert any('FIM DO MOTIVO.' in text for text in texts)


def test_camera_events_keep_local_quality_reason_and_uncertain_registration_after_lost_reply(store):
    api = Api()

    def lost(*args):
        raise Offline('private-lost-reply')

    api.finish_sample = lost
    events = []
    maintain_camera(store, api, None, None, events.append)
    assert [event['kind'] for event in events] == [
        'connected', 'processing', 'result_pending', 'analysis_error',
    ]
    status = DashboardStatus()
    for event in events:
        status.handle(event)
    assert 'Aprovada' in status.analysis and '(local)' in status.analysis
    assert status.analysis_detail == LOCAL_RESULT['reason']
    assert status.registration_tone == 'orange'
    assert 'pode ter recebido' in status.registration_detail
    assert 'private-lost-reply' not in status.registration_detail
    assert store.pending_sample_work() is not None
