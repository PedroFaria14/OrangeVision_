from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
import pytest
from backend.device.api import Offline
from backend.device.detector import ModelFailure, decode_oranges, preprocess
from backend.device.inspect import CaptureGate
from backend.device.samples import flush_camera_samples, sample_result
from backend.device.storage import Store
from test_vision import synthetic_calibration


def test_preprocessing_preserves_bgr_and_padding_without_imagenet_normalization():
    frame = np.full((1, 2, 3), (10, 20, 30), dtype=np.uint8)
    blob, ratio = preprocess(frame)
    assert blob.shape == (1, 3, 640, 640)
    assert blob.dtype == np.float32
    assert blob[0, :, 0, 0].tolist() == [10, 20, 30]
    assert blob[0, :, 500, 0].tolist() == [114, 114, 114]
    assert ratio == 320


def test_decode_applies_nms_and_does_not_treat_other_classes_as_oranges():
    output = np.zeros((1, 8400, 85), np.float32)
    for index in (0, 1):
        output[0, index, :4] = [12.5 - index, 12.5, np.log(50 / 8), np.log(50 / 8)]
        output[0, index, 4] = 1
        output[0, index, 54] = 0.9
    candidates = decode_oranges(output, (200, 200, 3), 1)
    assert len(candidates) == 1
    assert candidates[0]['score'] == pytest.approx(0.9)
    output[0, :, 5 + 47] = 1
    assert decode_oranges(output, (200, 200, 3), 1) == []


def test_incompatible_network_output_fails_closed():
    with pytest.raises(ModelFailure):
        decode_oranges(np.zeros((1, 1, 85)), (100, 100, 3), 1)


def test_capture_gate_requires_stability_then_removal_before_second_capture():
    gate = CaptureGate()
    detection = {'status': 'detected', 'box': [20, 20, 100, 100]}
    assert not gate.observe(detection, 0)
    assert not gate.observe(detection, 0.6)
    assert gate.observe(detection, 1.3)
    gate.captured()
    assert not gate.observe(detection, 5)
    assert not gate.observe({'status': 'ambiguous'}, 6)
    assert not gate.observe(detection, 8)
    gate.observe({'status': 'not_detected'}, 10)
    gate.observe({'status': 'not_detected'}, 11.1)
    assert not gate.observe(detection, 12)
    assert not gate.observe(detection, 12.6)
    assert gate.observe(detection, 13.3)


def test_automatic_start_requires_clear_area_before_arming():
    gate = CaptureGate(require_clear=True)
    detection = {'status': 'detected', 'box': [20, 20, 100, 100]}
    for stamp in (0, 1, 2, 3):
        assert not gate.observe(detection, stamp)
    gate.observe({'status': 'not_detected'}, 4)
    gate.observe({'status': 'not_detected'}, 5.1)
    assert not gate.observe(detection, 6)
    assert not gate.observe(detection, 6.6)
    assert gate.observe(detection, 7.3)


def test_camera_outbox_survives_offline_and_keeps_original_session(tmp_path, monkeypatch):
    store = Store(tmp_path / 'camera.db')
    store.initialize()
    original = {'id': str(uuid4()), 'lease_token': 'original-lease', 'state': 'active'}
    store.save_grant(original)
    command = str(uuid4())
    stamp = datetime.now(UTC).isoformat()
    store.save_camera_sample(command, original['id'], stamp, b'original-photo')
    store.save_camera_sample(command, original['id'], stamp, b'original-photo')
    store.save_grant({'id': str(uuid4()), 'lease_token': 'new-operator-lease', 'state': 'active'})

    class Api:
        offline = True

        def upload_camera_sample(self, grant, identity, captured_at, content):
            assert grant['id'] == original['id']
            assert grant['lease_token'] == 'original-lease'
            assert content == b'original-photo'
            if self.offline:
                raise Offline('synthetic disconnect')
            return {'id': str(uuid4()), 'source_inspection_id': original['id']}

    api = Api()
    monkeypatch.setattr('backend.device.samples.time.sleep', lambda _: None)
    with pytest.raises(Offline):
        flush_camera_samples(store, api)
    assert len(Store(store.path).pending_camera_samples()) == 1
    api.offline = False
    flush_camera_samples(Store(store.path), api)
    assert store.pending_camera_samples() == []
    assert store.camera_sample_counts() == {'synced': 1}


def test_outbox_conflicting_command_cannot_change_owner_or_photo(tmp_path):
    store = Store(tmp_path / 'camera.db')
    store.initialize()
    grant = {'id': str(uuid4())}
    store.save_grant(grant)
    command = str(uuid4())
    stamp = datetime.now(UTC).isoformat()
    store.save_camera_sample(command, grant['id'], stamp, b'first')
    with pytest.raises(RuntimeError):
        store.save_camera_sample(command, grant['id'], stamp, b'different')
    assert store.pending_camera_samples()[0]['image'] == b'first'


def test_detector_negative_cannot_produce_quality_category():
    import cv2

    class Negative:
        def detect(self, frame):
            return {
                'status': 'not_detected',
                'count': 0,
                'label': None,
                'score': None,
                'box': None,
                'model': 'synthetic',
                'inference_ms': 1,
            }

    image = cv2.imencode('.png', np.zeros((100, 100, 3), np.uint8))[1].tobytes()
    result = sample_result(image, detector=Negative())
    assert result['state'] == 'not_evaluable'
    assert result['classification'] is None
    assert result['metrics'] is None
    assert result['detection']['status'] == 'not_detected'


def test_headless_camera_does_not_require_highgui(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace

    import cv2
    from backend.device import inspect as app
    from backend.device.config import DeviceSettings

    settings = DeviceSettings(
        str(uuid4()),
        'http://127.0.0.1:8001',
        'test-only-credential' * 3,
        tmp_path / 'device.db',
        tmp_path / 'camera.lock',
        None,
        'usb',
        0,
        100,
        100,
    )
    monkeypatch.setattr(app.DeviceSettings, 'load', lambda: settings)
    calls = []

    class Camera:
        def __init__(self, settings):
            pass

        def capture(self):
            calls.append(True)
            if len(calls) > 3:
                raise KeyboardInterrupt
            return np.zeros((100, 100, 3), np.uint8)

        def close(self):
            pass

    monkeypatch.setattr(app, 'Camera', Camera)
    monkeypatch.setattr(
        app,
        'DeviceApi',
        lambda _: SimpleNamespace(
            heartbeat_samples=lambda *a: None, claim_sample=lambda _: None, close=lambda: None
        ),
    )
    monkeypatch.setattr(
        app,
        'OrangeDetector',
        lambda: SimpleNamespace(
            detect=lambda _: {'status': 'not_detected', 'box': None, 'count': 0, 'inference_ms': 1}
        ),
    )
    for name in ('namedWindow', 'imshow', 'waitKey', 'destroyAllWindows'):
        monkeypatch.setattr(
            cv2, name, lambda *a, **k: pytest.fail('Headless não deve abrir janelas.')
        )
    monkeypatch.setattr(sys, 'argv', ['inspect', '--headless'])
    app.main()
    assert len(calls) == 4


def test_ai_quality_requires_calibration_for_the_exact_segmentation_method():
    import cv2

    class Detector:
        def detect(self, frame):
            return {
                'status': 'detected',
                'label': 'orange',
                'box': [30, 30, 140, 140],
                'score': 0.9,
                'count': 1,
                'model': 'synthetic',
                'inference_ms': 1,
            }

    frame = np.zeros((200, 200, 3), np.uint8)
    cv2.circle(frame, (100, 100), 60, (0, 128, 255), -1)
    image = cv2.imencode('.png', frame)[1].tobytes()
    legacy = synthetic_calibration()
    result = sample_result(image, legacy, validated=True, detector=Detector())
    assert result['classification'] is None
    assert result['state'] == 'awaiting_review'
    calibration = {**legacy, 'segmentation_method': 'yolox-s-grabcut-v1'}
    calibration.pop('fruit_hsv')  # A IA não exige amostra manual F.
    result = sample_result(image, calibration, validated=True, detector=Detector())
    assert result['state'] == 'completed'
    assert result['classification'] == 'APROVADA'
    assert result['algorithm_version'] == 'yolox-s-grabcut-v1'
