import base64
from types import SimpleNamespace
from uuid import uuid4

import cv2
import numpy as np
import pytest
from backend.device.api import Offline
from backend.device.samples import process_one, run_samples, sample_result
from test_vision import synthetic_calibration


def image():
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.circle(frame, (100, 100), 60, (0, 128, 255), -1)
    return cv2.imencode('.png', frame)[1].tobytes()


def test_file_without_calibration_waits_for_evaluation_without_fake_metrics():
    result = sample_result(image())
    assert result['state'] == 'awaiting_review'
    assert result['metrics'] is None
    assert result['classification'] is None
    assert result['algorithm_version'] == 'image-acquisition-v1'


def test_draft_extracts_mask_but_never_promotes_itself_to_validated():
    result = sample_result(image(), synthetic_calibration(), validated=False)
    assert result['state'] == 'awaiting_review'
    assert result['classification'] is None
    assert result['metrics']['visual_score'] is None
    assert result['metrics']['orange_color_ratio'] == pytest.approx(1)
    mask = cv2.imdecode(
        np.frombuffer(base64.b64decode(result['mask_base64']), dtype=np.uint8), cv2.IMREAD_GRAYSCALE
    )
    assert mask.shape == (200, 200)
    assert set(np.unique(mask)) == {0, 255}


def test_validated_calibration_can_complete_experimental_sample():
    result = sample_result(image(), synthetic_calibration(), validated=True)
    assert result['state'] == 'completed'
    assert result['classification'] == 'APROVADA'
    assert result['calibration_validated'] is True


def test_invalid_file_does_not_become_review_classification():
    result = sample_result(b'not an image', synthetic_calibration())
    assert result['state'] == 'not_evaluable'
    assert result['metrics'] is None
    assert result['classification'] is None


def test_lost_claim_and_result_reuse_tokens_and_payload_without_reprocessing(monkeypatch):
    monkeypatch.setattr('backend.device.samples.time.sleep', lambda _: None)
    identity = str(uuid4())

    class Api:
        def __init__(self):
            self.claims = []
            self.results = []
            self.downloads = 0

        def claim_sample(self, attempt):
            self.claims.append(dict(attempt))
            if len(self.claims) == 1:
                raise Offline('synthetic lost reply')
            return {'id': identity, 'image_url': 'https://untrusted.example/ignored'}

        def sample_image(self, received, lease):
            assert received == identity
            assert lease == self.claims[0]['lease_token']
            self.downloads += 1
            return image()

        def finish_sample(self, received, lease, payload):
            self.results.append((received, lease, payload))
            if len(self.results) == 1:
                raise Offline('synthetic lost ACK')
            return {'state': payload['state']}

    api = Api()
    assert process_one(api) == {'id': identity, 'state': 'awaiting_review'}
    assert api.claims[0] == api.claims[1]
    assert api.results[0] == api.results[1]
    assert api.downloads == 1


def test_loop_keeps_polling_after_transient_disconnection(monkeypatch, capsys):
    calls = []
    sleeps = []

    def process(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise Offline('private-error-detail')
        return None

    def pause(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise KeyboardInterrupt

    monkeypatch.setattr('backend.device.samples.process_one', process)
    monkeypatch.setattr('backend.device.samples.time.sleep', pause)
    with pytest.raises(KeyboardInterrupt):
        run_samples(SimpleNamespace(heartbeat_samples=lambda *args: None), loop=True)
    assert len(calls) == 2
    output = capsys.readouterr().out
    assert 'permanece no servidor' in output
    assert 'private-error-detail' not in output
