import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from backend.device.vision import METRICS, CalibratedVision, VisionFailure


def synthetic_calibration():
    # SOMENTE imagem sintética dos testes, não usar estes limiares em frutas reais.
    return {
        'version': 'synthetic-tests-only',
        'validated': True,
        'minimum_fruit_area_pixels': 50,
        'fruit_hsv': [[[1, 100, 100], [30, 255, 255]]],
        'orange_hsv': [[[10, 100, 100], [25, 255, 255]]],
        'abnormal_hsv': [[[0, 0, 0], [179, 255, 80]]],
        'score_rules': {
            key: {
                'low': 0,
                'high': 1,
                'weight': 1,
                'direction': 'lower' if key in ('asymmetry', 'abnormal_region_ratio') else 'higher',
            }
            for key in METRICS
        },
        'attention_min_score': 50,
        'approval_min_score': 90,
    }


def test_unfilled_example_is_not_a_fake_production_calibration():
    example = json.loads((Path(__file__).parents[1] / 'calibration.example.json').read_text())
    with pytest.raises(VisionFailure):
        CalibratedVision(example)


def test_metrics_are_measured_only_inside_segmented_synthetic_roi():
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.circle(frame, (100, 100), 60, (0, 128, 255), -1)
    result = CalibratedVision(synthetic_calibration()).analyze(frame)
    assert result['metrics']['orange_color_ratio'] == pytest.approx(1)
    assert result['metrics']['abnormal_region_ratio'] == 0
    assert result['metrics']['asymmetry'] == 0
    assert 0.7 < result['metrics']['circularity'] < 1.1
    assert result['classification'] == 'APROVADA'
    assert 'experimental' in result['reason']


def test_invalid_acquisition_and_missing_fruit_do_not_return_a_class():
    engine = CalibratedVision(synthetic_calibration())
    for frame in (None, np.zeros((200, 200, 3), dtype=np.uint8)):
        with pytest.raises(VisionFailure):
            engine.analyze(frame)
