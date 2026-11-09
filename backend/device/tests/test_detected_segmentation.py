from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from backend.device import segmentation
from backend.device.samples import sample_result
from backend.device.segmentation import SelectionBoundaryFailure, VisionFailure, segment_detected


def test_selection_limit_expands_margin_only_for_boundary_failures(monkeypatch):
    rectangles = []
    expected = object()

    def guided(frame, rectangle, minimum_area):
        rectangles.append(rectangle)
        if len(rectangles) == 1:
            raise SelectionBoundaryFailure('synthetic-tight-crop')
        return expected

    monkeypatch.setattr(segmentation, 'segment_guided', guided)
    result = segment_detected(np.zeros((200, 200, 3), np.uint8), [70, 70, 40, 40])
    assert result is expected
    assert len(rectangles) == 2
    assert rectangles[1][0] < rectangles[0][0]
    assert rectangles[1][2] > rectangles[0][2]


def test_boundary_safety_is_not_disabled_when_all_crops_fail(monkeypatch):
    rectangles = []

    def guided(frame, rectangle, minimum_area):
        rectangles.append(rectangle)
        raise SelectionBoundaryFailure('synthetic-tight-crop')

    monkeypatch.setattr(segmentation, 'segment_guided', guided)
    with pytest.raises(SelectionBoundaryFailure, match='mesmo após'):
        segment_detected(np.zeros((200, 200, 3), np.uint8), [70, 70, 40, 40])
    assert len(rectangles) == 3


def test_other_segmentation_failures_are_not_ignored_or_retried(monkeypatch):
    rectangles = []

    def guided(frame, rectangle, minimum_area):
        rectangles.append(rectangle)
        raise VisionFailure('synthetic-low-contrast')

    monkeypatch.setattr(segmentation, 'segment_guided', guided)
    with pytest.raises(VisionFailure, match='low-contrast'):
        segment_detected(np.zeros((200, 200, 3), np.uint8), [70, 70, 40, 40])
    assert len(rectangles) == 1


def test_fruit_at_real_photo_edge_never_gets_quality_classification():
    frame = np.zeros((200, 200, 3), np.uint8)
    cv2.circle(frame, (0, 100), 50, (0, 128, 255), -1)
    content = cv2.imencode('.png', frame)[1].tobytes()
    detector = SimpleNamespace(detect=lambda _: {
        'status': 'detected', 'count': 1, 'box': [0, 50, 51, 101],
    })
    result = sample_result(content, detector=detector)
    assert result['state'] == 'not_evaluable'
    assert 'borda da foto' in result['reason']
    assert result['classification'] is None
    assert result['calibration_validated'] is False


def test_valid_single_fruit_still_segments_without_changing_source_pixels():
    frame = np.zeros((200, 200, 3), np.uint8)
    cv2.circle(frame, (100, 100), 50, (0, 128, 255), -1)
    before = frame.copy()
    segment = segment_detected(frame, [50, 50, 101, 101])
    assert not segment.touches_border
    assert segment.area > 7000
    assert np.array_equal(frame, before)
