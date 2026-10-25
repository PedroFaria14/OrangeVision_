from concurrent.futures import Future
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import cv2
import numpy as np
import pytest
from backend.device.api import ApiFailure
from backend.device.camera_review import CameraReview, CaptureNotAuthorized, confirm_photo
from backend.device.camera_window import action_at, render_frame, run_window
from backend.device.storage import Store


@pytest.fixture
def context(tmp_path):
    store = Store(tmp_path / 'review.db')
    store.initialize()
    grant = {'id': str(uuid4()), 'lease_token': 'test-only-original-lease'}
    store.save_grant(grant)
    frame = np.full((240, 320, 3), (10, 120, 220), np.uint8)
    detection = {
        'status': 'detected',
        'count': 1,
        'box': [50, 50, 100, 100],
        'score': 0.9,
        'model': 'synthetic-test',
        'inference_ms': 1,
        'label': 'orange',
    }
    return store, grant, frame, detection


def test_detected_photo_is_saved_without_waiting_for_network_or_authorization(context):
    store, grant, frame, detection = context
    store.deactivate(grant['id'])
    review = CameraReview(store)
    assert review.take(frame, detection, datetime.now(UTC).isoformat(), None)
    assert store.camera_sample_counts() == {}  # Ainda não houve Usar esta foto.
    assert store.latest_photo_draft()['image']
    assert not review.take(frame, detection, datetime.now(UTC).isoformat(), None)
    restored = CameraReview(Store(store.path))
    assert restored.photo.identity == review.photo.identity
    assert restored.photo.grant is None
    with pytest.raises(CaptureNotAuthorized, match='Foto guardada'):
        confirm_photo(SimpleNamespace(store=store), restored.photo)
    assert store.latest_photo_draft()['id'] == review.photo.identity


def test_non_detected_frame_does_not_become_a_labeled_photo(context):
    store, grant, frame, detection = context
    review = CameraReview(store)
    assert not review.take(
        frame, {**detection, 'status': 'not_detected'}, datetime.now(UTC).isoformat(), grant
    )
    assert review.photo is None
    assert store.latest_photo_draft() is None


def test_confirmation_preserves_original_operator_and_exact_bytes(context):
    store, grant, frame, detection = context
    review = CameraReview(store)
    review.take(frame, detection, datetime.now(UTC).isoformat(), grant)
    saved = store.latest_photo_draft()
    original_id = grant['id']
    store.save_grant({'id': str(uuid4()), 'lease_token': 'another-operator'})

    def authorized(frozen):
        assert frozen['id'] == original_id
        return frozen

    worker = SimpleNamespace(store=store, _capture_grant=authorized)
    confirm_photo(worker, review.photo)
    confirm_photo(worker, review.photo)
    rows = store.pending_camera_samples()
    assert len(rows) == 1
    assert rows[0]['session_id'] == original_id
    assert rows[0]['image'] == saved['image']
    assert store.latest_photo_draft() is None


def test_confirmation_rollback_keeps_review_photo(context, monkeypatch):
    store, grant, frame, detection = context
    review = CameraReview(store)
    review.take(frame, detection, datetime.now(UTC).isoformat(), grant)
    original = store._save_camera_sample

    def fail(db, *args):
        original(db, *args)
        raise RuntimeError('synthetic failure before commit')

    monkeypatch.setattr(store, '_save_camera_sample', fail)
    with pytest.raises(RuntimeError):
        confirm_photo(SimpleNamespace(store=store, _capture_grant=lambda g: g), review.photo)
    assert store.pending_camera_samples() == []
    assert store.latest_photo_draft()['image']


def test_retake_is_explicit_and_does_not_require_removing_the_fruit(context):
    store, grant, frame, detection = context
    review = CameraReview(store)
    review.take(frame, detection, datetime.now(UTC).isoformat(), grant)
    previous = review.photo.identity
    review.sending = True
    assert not review.retake()
    review.sending = False
    assert review.retake()
    assert review.take(frame, detection, datetime.now(UTC).isoformat(), grant)
    assert review.photo.identity != previous
    assert store.camera_sample_counts() == {}


@pytest.mark.parametrize('allowed', [True, False])
def test_saved_photo_can_be_reauthorized_only_after_server_owner_check(context, allowed):
    from backend.device.samples import flush_camera_samples

    store, original, frame, detection = context
    review = CameraReview(store)
    review.take(frame, detection, datetime.now(UTC).isoformat(), original)
    original_bytes = store.latest_photo_draft()['image']
    current = {'id': str(uuid4()), 'lease_token': 'new-test-lease'}
    store.save_grant(current)
    calls = []

    class Api:
        def authorize_camera_review(self, source, authorization):
            assert source['id'] == original['id'] and authorization['id'] == current['id']
            calls.append('owner-check')
            if not allowed:
                raise ApiFailure(403)

        def upload_camera_review(self, source, authorization, identity, stamp, content):
            assert source['id'] == original['id']
            assert authorization['id'] == current['id']
            assert content == original_bytes
            calls.append('upload')
            return {
                'id': str(uuid4()),
                'source_inspection_id': source['id'],
                'review_authorization_id': authorization['id'],
            }

    def authorize(grant):
        if grant['id'] == original['id']:
            raise RuntimeError('expired')
        return grant

    worker = SimpleNamespace(store=store, api=Api(), _capture_grant=authorize)
    if not allowed:
        with pytest.raises(CaptureNotAuthorized, match='conta original'):
            confirm_photo(worker, review.photo)
        assert store.latest_photo_draft()['image'] == original_bytes
        assert not store.pending_camera_samples()
    else:
        confirm_photo(worker, review.photo)
        row = store.pending_camera_samples()[0]
        assert row['session_id'] == original['id'] and row['review_grant_id'] == current['id']
        flush_camera_samples(store, worker.api)
        assert calls == ['owner-check', 'upload']
        assert store.camera_sample_counts() == {'synced': 1}


def test_caption_is_above_detected_box_and_buttons_match_review(context, monkeypatch):
    _, _, frame, detection = context
    texts = []
    original = cv2.putText

    def record(image, text, position, *args, **kwargs):
        texts.append((text, position))
        return original(image, text, position, *args, **kwargs)

    monkeypatch.setattr(cv2, 'putText', record)
    result = render_frame(
        frame, detection, False, False, False, False, False, 'Pronto', 'Conectado'
    )
    assert result.shape == (720, 960, 3)
    assert any(text == 'Laranja' and position[1] < 50 for text, position in texts)
    assert not any('Retire a fruta' in text for text, _ in texts)
    assert action_at(50, 580, False) == 'capture'
    assert action_at(50, 580, True) == 'use'
    assert action_at(300, 580, True) == 'retake'
    assert action_at(600, 580, True) == 'connect'


class ControlledPool:
    def __init__(self):
        self.tasks = []

    def submit(self, operation, *args):
        future = Future()
        self.tasks.append((future, operation, args))
        return future

    def finish(self):
        for future, operation, args in self.tasks:
            if not future.done():
                try:
                    future.set_result(operation(*args))
                except Exception as error:
                    future.set_exception(error)


def test_connect_button_keeps_saved_photo_until_use_without_closing_camera(context, monkeypatch):
    from backend.device import camera_window as window

    store, original, frame, detection = context
    review = CameraReview(store)
    review.take(frame, detection, datetime.now(UTC).isoformat(), original)
    saved_id = review.photo.identity
    current = {'id': str(uuid4()), 'lease_token': 'new-session'}
    pool = ControlledPool()
    captured = []

    def authorize(grant):
        if grant['id'] == original['id']:
            raise RuntimeError('expired')
        return grant

    worker = SimpleNamespace(
        store=store,
        _capture_grant=authorize,
        pair=lambda code: store.save_grant(current),
        api=SimpleNamespace(authorize_camera_review=lambda old, new: {'authorized': True}),
    )
    api = SimpleNamespace(heartbeat_samples=lambda *a: None, claim_sample=lambda _: None)
    monkeypatch.setattr(
        'backend.device.session_dialog.ask_connection_code', lambda _: ('test-code', False)
    )
    monkeypatch.setattr(window, 'render_frame', lambda *a: np.zeros((720, 960, 3), np.uint8))
    for name in ('namedWindow', 'resizeWindow', 'setMouseCallback', 'imshow'):
        monkeypatch.setattr(cv2, name, lambda *a, **k: None)
    monkeypatch.setattr(cv2, 'getWindowProperty', lambda *a: 1)
    step = [0]

    def key(delay):
        step[0] += 1
        if step[0] == 2:
            return ord('p')
        if step[0] == 3:
            pool.finish()
        if step[0] == 4:
            assert store.latest_photo_draft()['id'] == saved_id
            assert not captured
            return ord('u')
        if step[0] == 5:
            pool.finish()
        return ord('q') if step[0] >= 7 else -1

    monkeypatch.setattr(cv2, 'waitKey', key)
    gate = SimpleNamespace(
        armed=False, observe=lambda *a: False, captured=lambda: captured.append(True)
    )
    run_window(
        SimpleNamespace(capture=lambda: frame.copy()),
        SimpleNamespace(detect=lambda _: detection),
        worker,
        api,
        pool,
        gate,
        False,
        False,
        None,
        lambda *a: None,
    )
    assert store.pending_camera_samples()[0]['id'] == saved_id
    assert store.pending_camera_samples()[0]['review_grant_id'] == current['id']
    assert captured == [True]


@pytest.mark.parametrize('authorized', [True, False])
def test_manual_capture_works_during_poll_and_never_hides_confirmation_error(
    context, monkeypatch, authorized
):
    from backend.device import camera_window as window

    store, grant, frame, detection = context
    pool = ControlledPool()
    camera = SimpleNamespace(capture=lambda: frame.copy())
    detector = SimpleNamespace(detect=lambda _: dict(detection))
    gate = SimpleNamespace(
        observe=lambda *a: False, armed=False, captured=lambda: captured.append(True)
    )
    captured = []

    def authorize(frozen):
        if not authorized:
            raise RuntimeError('synthetic inactive session')
        return frozen

    worker = SimpleNamespace(store=store, _capture_grant=authorize)
    api = SimpleNamespace(heartbeat_samples=lambda *a: None, claim_sample=lambda _: None)
    notices = []

    def render(*args):
        notices.append((args[-2], args[-1]))
        return np.zeros((720, 960, 3), np.uint8)

    monkeypatch.setattr(window, 'render_frame', render)
    for name in ('namedWindow', 'resizeWindow', 'setMouseCallback', 'imshow'):
        monkeypatch.setattr(cv2, name, lambda *a, **k: None)
    monkeypatch.setattr(cv2, 'getWindowProperty', lambda *a: 1)
    iteration = [0]

    def key(delay):
        iteration[0] += 1
        if iteration[0] == 2:
            assert len(pool.tasks) == 1 and not pool.tasks[0][0].done()
            return ord('c')
        if iteration[0] == 3:
            assert store.latest_photo_draft() and not store.pending_camera_samples()
            return ord('u')
        if iteration[0] == 4:
            pool.finish()
        return ord('q') if iteration[0] >= 6 else -1

    monkeypatch.setattr(cv2, 'waitKey', key)
    run_window(
        camera,
        detector,
        worker,
        api,
        pool,
        gate,
        False,
        False,
        None,
        lambda *a: pytest.fail('Captura manual não usa automático.'),
    )
    assert len(pool.tasks) == 2  # consulta + confirmação, sem perder C/U.
    if authorized:
        assert len(store.pending_camera_samples()) == 1
        assert captured == [True]
    else:
        assert store.latest_photo_draft()['image']
        assert captured == []
        assert any(
            'Foto guardada' in capture and connection == 'Executor conectado.'
            for capture, connection in notices
        )
