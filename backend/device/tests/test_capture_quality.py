"""Sombra não é mancha, pontes de fundo são cortadas e o aviso ao vivo orienta a captura."""

import copy

import cv2
import numpy as np
import pytest
from backend.device import calibrate
from backend.device.camera_dashboard import render_frame
from backend.device.framing import BEST, framing_hint, safe_framing_hint
from backend.device.segmentation import (
    ColorLocateFailure,
    VisionFailure,
    measure_metrics,
    segment_single_by_color,
)
from backend.device.vision import CalibratedVision

ORANGE, BROWN = (0, 140, 255), (20, 50, 90)
CAL = calibrate.DEFAULT_CALIBRATION
RULE = CAL['abnormal_detection']


def shaded_fruit(center=(160, 120), radius=70):
    """Laranja limpa com sombra suave na metade de baixo, sobre fundo claro."""
    frame = np.full((240, 320, 3), 235, np.uint8)
    mask = np.zeros(frame.shape[:2], np.uint8)
    cv2.circle(mask, center, radius, 255, -1)
    rows = np.arange(frame.shape[0], dtype=np.float32)[:, None]
    # Brilho cai até ~45% na base: degradê largo, como luz vinda de cima.
    shade = np.clip(1 - 0.55 * (rows - (center[1] - radius)) / (2 * radius), 0.45, 1)
    peel = (np.array(ORANGE, np.float32) * shade[..., None]).astype(np.uint8)
    frame[mask > 0] = np.broadcast_to(peel, frame.shape)[mask > 0]
    return frame


def stains(frame, rule):
    segment = segment_single_by_color(frame, CAL['fruit_hsv'], 1000)
    return measure_metrics(segment, CAL['orange_hsv'], CAL['abnormal_hsv'], rule)[
        'abnormal_region_ratio'
    ]


def test_shadow_counts_as_stain_only_with_old_ranges():
    frame = shaded_fruit()
    assert stains(frame, None) > 0.10  # faixa marrom absoluta: sombra vira "mancha"
    assert stains(frame, RULE) < 0.03


def test_real_spots_are_still_counted_on_shaded_fruit():
    frame = shaded_fruit()
    for angle in np.linspace(0, 2 * np.pi, 6, endpoint=False):
        cv2.circle(frame, (int(160 + 35 * np.cos(angle)), int(120 + 35 * np.sin(angle))), 10, BROWN, -1)
    assert stains(frame, RULE) > CAL['classification_rules']['passou_min_abnormal_ratio']


def test_thin_background_bridge_is_cut_instead_of_rejecting_border():
    frame = shaded_fruit()
    # Faixa fina com cor de fruta (ex.: borda de teclado) ligando a fruta à borda da foto.
    cv2.rectangle(frame, (225, 116), (319, 124), ORANGE, -1)
    segment = segment_single_by_color(frame, CAL['fruit_hsv'], 1000)
    assert not segment.touches_border
    assert segment.area > np.pi * 70 * 70 * 0.85


@pytest.mark.parametrize(
    ('change', 'code'),
    [('edge', 'border'), ('two', 'multiple'), ('empty', 'none'), ('tiny', 'small')],
)
def test_color_refusals_carry_a_code(change, code):
    frame = shaded_fruit(center=(40, 120), radius=90) if change == 'edge' else shaded_fruit()
    if change == 'two':
        frame = np.full((240, 320, 3), 235, np.uint8)
        cv2.circle(frame, (80, 120), 50, ORANGE, -1)
        cv2.circle(frame, (240, 120), 50, ORANGE, -1)
    elif change == 'empty':
        frame = np.full((240, 320, 3), 235, np.uint8)
    elif change == 'tiny':
        frame = np.full((240, 320, 3), 235, np.uint8)
        cv2.circle(frame, (160, 120), 20, ORANGE, -1)
    with pytest.raises(ColorLocateFailure) as error:
        segment_single_by_color(frame, CAL['fruit_hsv'], 8000)
    assert error.value.code == code


@pytest.mark.parametrize(
    'rule',
    [
        {'method': 'other', 'min_relative_contrast': 0.25},
        {'method': 'contrast-v1'},
        {'method': 'contrast-v1', 'min_relative_contrast': 2},
        {'method': 'contrast-v1', 'min_relative_contrast': 0.25, 'max_stain_fraction': 0.9},
        {'method': 'contrast-v1', 'min_relative_contrast': 0.25, 'highlight_percentile': 10},
    ],
)
def test_invalid_stain_rule_is_rejected(rule):
    value = copy.deepcopy(CAL)
    value.update(validated=True, abnormal_detection=rule)
    with pytest.raises(VisionFailure):
        CalibratedVision(value)


def test_framing_hint_guides_capture_without_touching_the_frame():
    good = shaded_fruit()
    original = good.copy()
    hint = framing_hint(good, CAL)
    assert (hint.tone, hint.message) == ('green', BEST)
    assert hint.contour is not None
    canvas = render_frame(
        good, {'status': 'not_detected', 'count': 0}, False, False, False, False, False,
        'ok', 'ok', framing=hint,
    )
    assert canvas.shape == (720, 960, 3)
    assert np.array_equal(good, original)  # o quadro segue intacto para a IA/captura
    assert framing_hint(shaded_fruit(center=(40, 120), radius=90), CAL).tone == 'red'
    assert 'borda' in framing_hint(shaded_fruit(center=(40, 120), radius=90), CAL).message
    assert framing_hint(good, None) is None
    assert safe_framing_hint(np.zeros((2, 2), np.uint8), CAL) is None


def test_framing_hint_warns_about_colored_background():
    frame = shaded_fruit()
    frame[:, :60] = ORANGE  # objeto colorido separado da fruta, ocupando o fundo
    hint = framing_hint(frame, CAL)
    assert hint.tone in ('orange', 'red')
    assert hint.message != BEST
