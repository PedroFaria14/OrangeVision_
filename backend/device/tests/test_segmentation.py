import cv2
import numpy as np
import pytest
from backend.device.lab_preview import preview_frame
from backend.device.segmentation import (
    VisionFailure,
    measure_metrics,
    segment_fruit,
    validate_ranges,
)
from backend.device.vision import CalibratedVision
from test_vision import synthetic_calibration


@pytest.fixture
def fruit_image():
    image = np.zeros((180, 240, 3), dtype=np.uint8)
    cv2.circle(image, (120, 90), 55, (0, 128, 255), -1)
    return image


def test_preview_requires_sample_and_never_invents_a_class(fruit_image):
    canvas, result = preview_frame(fruit_image, {})
    assert canvas.shape == (480, 1080, 3)
    assert result['status'] == 'awaiting_sample'
    assert result['metrics'] == {}
    assert result['classification'] is None
    assert result['species_verified'] is False


def test_missing_color_samples_are_unavailable_not_zero(fruit_image):
    calibration = synthetic_calibration()
    segment = segment_fruit(fruit_image, calibration['fruit_hsv'])
    metrics = measure_metrics(segment)
    assert metrics['orange_color_ratio'] is None
    assert metrics['abnormal_region_ratio'] is None
    assert 0.8 < metrics['circularity'] < 1.1
    assert metrics['asymmetry'] == pytest.approx(0)


def test_preview_and_classifier_measure_the_same_pixels_without_mutating_input(fruit_image):
    original = fruit_image.copy()
    calibration = synthetic_calibration()
    classifier = CalibratedVision(calibration)
    _, preview = preview_frame(fruit_image, calibration, classifier)
    measured = classifier.analyze(fruit_image)
    assert preview['status'] == 'candidate'
    assert preview['classification'] == measured['classification']
    assert preview['visual_score'] == measured['metrics']['visual_score']
    for key, value in preview['metrics'].items():
        assert value == measured['metrics'][key]
    assert np.array_equal(fruit_image, original)


def test_draft_never_enables_classifier_even_when_injected(fruit_image):
    class ForbiddenClassifier:
        def analyze(self, frame):
            pytest.fail('Rascunho não pode classificar.')

    calibration = {**synthetic_calibration(), 'validated': False}
    _, result = preview_frame(fruit_image, calibration, ForbiddenClassifier())
    assert result['status'] == 'candidate'
    assert result['metrics']['orange_color_ratio'] == 1
    assert result['classification'] is None
    assert result['visual_score'] is None


def test_cropped_contour_blocks_preview_metrics_and_production_classification():
    frame = np.zeros((180, 240, 3), dtype=np.uint8)
    cv2.circle(frame, (0, 90), 55, (0, 128, 255), -1)
    calibration = synthetic_calibration()
    _, result = preview_frame(frame, calibration, CalibratedVision(calibration))
    assert result['status'] == 'not_evaluable'
    assert 'borda' in result['reason']
    assert result['classification'] is None
    assert result['metrics'] == {}
    with pytest.raises(VisionFailure, match='borda'):
        CalibratedVision(calibration).analyze(frame)


def test_blank_image_and_small_noise_do_not_return_a_category():
    calibration = {**synthetic_calibration(), 'minimum_fruit_area_pixels': 100}
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    for radius in (0, 2):
        cv2.circle(frame, (50, 50), radius, (0, 128, 255), -1)
        _, result = preview_frame(frame, calibration)
        assert result['status'] == 'not_evaluable'
        assert result['classification'] is None


@pytest.mark.parametrize(
    'ranges', [None, [], [[1, 2]], [[[40, 0, 0], [20, 255, 255]]], [[[0, 0, 0], [180, 255, 255]]]]
)
def test_invalid_hsv_ranges_are_rejected(ranges):
    with pytest.raises(VisionFailure):
        validate_ranges(ranges)


def test_largest_region_mask_excludes_other_objects(fruit_image):
    cv2.circle(fruit_image, (20, 20), 5, (0, 128, 255), -1)
    segment = segment_fruit(fruit_image, synthetic_calibration()['fruit_hsv'])
    assert segment.mask[20, 20] == 0
    assert segment.mask[90, 120] == 255
    assert not segment.touches_border
