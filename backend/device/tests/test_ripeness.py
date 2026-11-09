"""Boa / Verde / Passou com imagens sintéticas; nenhum limiar aqui vale para campo."""

import copy
import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from backend.device import calibrate
from backend.device.camera_review import CameraReview
from backend.device.samples import sample_result
from backend.device.segmentation import VisionFailure, segment_single_by_color
from backend.device.vision import CalibratedVision

ORANGE, GREEN, BROWN = (0, 140, 255), (40, 180, 60), (20, 50, 90)
NOT_DETECTED = {'status': 'not_detected', 'label': None, 'score': None, 'box': None,
                'count': 0, 'model': 'synthetic', 'inference_ms': 1.0}


def calibration(**changes):
    value = copy.deepcopy(calibrate.DEFAULT_CALIBRATION)
    value.update(validated=True, version='synthetic-ripeness', **changes)
    return value


def fruit(color=ORANGE, spots=0, center=(160, 120), radius=70):
    frame = np.full((240, 320, 3), 235, np.uint8)  # fundo neutro claro
    cv2.circle(frame, center, radius, color, -1)
    for index in range(spots):
        angle = index * 2 * np.pi / max(spots, 1)
        spot = (int(center[0] + 35 * np.cos(angle)), int(center[1] + 35 * np.sin(angle)))
        cv2.circle(frame, spot, 14, BROWN, -1)
    return frame


def encoded(frame):
    return cv2.imencode('.png', frame)[1].tobytes()


def undetected(_frame):
    return dict(NOT_DETECTED)


@pytest.mark.parametrize(
    ('frame', 'expected', 'label'),
    [
        (fruit(ORANGE), 'APROVADA', 'Boa'),
        (fruit(GREEN), 'ATENCAO', 'Verde'),
        (fruit(ORANGE, spots=6), 'REVISAR', 'Passou'),
    ],
)
def test_color_rules_separate_good_green_and_spoiled(frame, expected, label):
    vision = CalibratedVision(calibration())
    segment = segment_single_by_color(frame, vision.calibration['fruit_hsv'], 1000)
    result = vision.classify_segment(segment)
    assert result['classification'] == expected
    assert result['reason'].startswith(label)
    assert set(result['metrics']) == {
        'orange_color_ratio', 'abnormal_region_ratio', 'circularity', 'asymmetry', 'visual_score',
    }


def test_detector_miss_uses_color_and_never_claims_ai_detection():
    detector = SimpleNamespace(detect=undetected)
    result = sample_result(encoded(fruit(GREEN)), calibration(), validated=True, detector=detector)
    assert result['state'] == 'completed'
    assert result['classification'] == 'ATENCAO'
    assert result['detection'] is None
    assert result['algorithm_version'] == 'opencv-hsv-fallback-v1'
    assert len(result['algorithm_version']) <= 50
    assert result['reason'].startswith('Fruta localizada pela cor')
    assert all(value is not None for value in result['metrics'].values())
    assert result['mask_base64']


def test_without_color_fallback_detector_miss_stays_not_evaluable():
    detector = SimpleNamespace(detect=undetected)
    result = sample_result(
        encoded(fruit(GREEN)), calibration(color_fallback=False), validated=True, detector=detector
    )
    assert result['state'] == 'not_evaluable'
    assert result['classification'] is None


def test_unvalidated_calibration_never_uses_color_fallback():
    detector = SimpleNamespace(detect=undetected)
    result = sample_result(encoded(fruit(GREEN)), calibration(), validated=False, detector=detector)
    assert result['state'] == 'not_evaluable'
    assert result['classification'] is None


def test_two_fruits_or_fruit_at_edge_are_rejected_by_color_fallback():
    detector = SimpleNamespace(detect=undetected)
    two = fruit(ORANGE, center=(80, 120), radius=50)
    cv2.circle(two, (240, 120), 50, GREEN, -1)
    result = sample_result(encoded(two), calibration(), validated=True, detector=detector)
    assert result['state'] == 'not_evaluable'
    assert 'Mais de uma fruta' in result['reason']
    edge = fruit(ORANGE, center=(40, 120), radius=90)
    result = sample_result(encoded(edge), calibration(), validated=True, detector=detector)
    assert result['state'] == 'not_evaluable'
    assert 'borda' in result['reason']


def test_internal_spots_stay_inside_the_fruit_mask():
    frame = fruit(ORANGE, spots=6)
    segment = segment_single_by_color(frame, calibrate.DEFAULT_CALIBRATION['fruit_hsv'], 1000)
    assert segment.area > np.pi * 70 * 70 * 0.9


@pytest.mark.parametrize(
    'change',
    [
        {'method': 'other'},
        {'verde_min_green_ratio': 1.5},
        {'boa_max_abnormal_ratio': 0.2},
        {'boa_max_green_ratio': 0.5},
        {'green_hsv': []},
    ],
)
def test_inconsistent_rules_are_rejected(change):
    value = calibration()
    value['classification_rules'].update(change)
    with pytest.raises(VisionFailure):
        CalibratedVision(value)


def test_color_fallback_requires_fruit_ranges():
    with pytest.raises(VisionFailure):
        CalibratedVision(calibration(fruit_hsv=[]))
    with pytest.raises(VisionFailure):
        CalibratedVision(calibration(color_fallback='sim'))


def test_manual_capture_without_detection_only_when_allowed():
    store = SimpleNamespace(save_photo_draft=lambda *args: None)
    review = CameraReview.__new__(CameraReview)
    review.store, review.photo, review.sending = store, None, False
    frame = fruit(GREEN)
    assert not review.take(frame, dict(NOT_DETECTED), '2026-11-08T12:00:00+00:00', None)
    assert review.take(
        frame, dict(NOT_DETECTED), '2026-11-08T12:00:00+00:00', None, allow_undetected=True
    )


def test_calibration_tool_marks_validated_only_when_all_labels_match(tmp_path):
    for folder, frame in (
        ('aprovadas', fruit(ORANGE)),
        ('verde', fruit(GREEN)),
        ('passou', fruit(ORANGE, spots=6)),
    ):
        (tmp_path / folder).mkdir()
        cv2.imwrite(str(tmp_path / folder / f'{folder}.png'), frame)
    output = tmp_path / 'calibracao.json'
    args = ['--fotos', str(tmp_path), '--saida', str(output), '--sem-detector', '--marcar-validada']
    assert calibrate.main(args) == 0
    saved = json.loads(output.read_text(encoding='utf-8'))
    assert saved['validated'] is True
    assert saved['validation_report']['hits'] == 3
    CalibratedVision(saved)

    cv2.imwrite(str(tmp_path / 'aprovadas' / 'errada.png'), fruit(GREEN))
    assert calibrate.main(args) == 1
    assert json.loads(output.read_text(encoding='utf-8'))['validated'] is False
