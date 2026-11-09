import threading
import time
from types import SimpleNamespace

import numpy as np
from backend.device.live_detection import DetectionSnapshot, LiveDetection


def wait_result(live, minimum):
    deadline = time.monotonic() + 3
    with live.condition:
        while live.result is None or live.result.sequence < minimum:
            remaining = deadline - time.monotonic()
            assert remaining > 0, 'Detector did not publish a result.'
            live.condition.wait(timeout=min(0.01, remaining))
        return live.result


def test_worker_keeps_only_latest_pending_frame_and_matching_detection():
    entered, release = threading.Event(), threading.Event()
    seen = []

    def detect(frame):
        value = int(frame[0, 0, 0])
        seen.append(value)
        if value == 1:
            entered.set()
            assert release.wait(3)
        return {'status': 'detected', 'value': value}

    live = LiveDetection(SimpleNamespace(detect=detect), interval=0)
    live.start()
    try:
        frame = np.ones((2, 2, 3), np.uint8)
        live.submit(frame, 'first', time.monotonic())
        assert entered.wait(3)
        live.submit(frame * 2, 'discarded', time.monotonic())
        last = live.submit(frame * 3, 'last', time.monotonic())
        frame[:] = 99
        release.set()
        result = wait_result(live, last)
        assert seen == [1, 3]
        assert result.frame[0, 0, 0] == result.detection['value'] == 3
        assert result.captured_at == 'last'
        assert result.fresh(time.monotonic())
    finally:
        release.set()
        live.close()
    assert not live.thread.is_alive()


def test_reset_discards_results_from_previous_review_generation():
    entered, release = threading.Event(), threading.Event()

    def detect(frame):
        entered.set()
        assert release.wait(3)
        return {'status': 'detected'}

    live = LiveDetection(SimpleNamespace(detect=detect), interval=0)
    live.start()
    try:
        live.submit(np.ones((2, 2, 3), np.uint8), 'old', time.monotonic())
        assert entered.wait(3)
        live.reset()
        release.set()
    finally:
        release.set()
        live.close()
    assert live.latest() == (None, None)


def test_stale_results_cannot_be_used_for_capture():
    snapshot = DetectionSnapshot(1, None, 'stamp', 10, {'status': 'detected'}, 11)
    assert snapshot.fresh(11.5)
    assert not snapshot.fresh(14)
    assert not DetectionSnapshot(1, None, 'stamp', 0, {}, 11).fresh(11)
