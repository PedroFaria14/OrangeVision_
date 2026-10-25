import json
import sys

import cv2
import numpy as np
import pytest
from backend.device import lab
from backend.device.lab_preview import preview_frame
from backend.device.segmentation import VisionFailure, segment_guided


def fruit_frame():
    frame = np.full((180, 240, 3), 230, dtype=np.uint8)
    cv2.circle(frame, (120, 90), 40, (0, 128, 255), -1)
    return frame


def test_guided_selection_separates_object_without_hsv_samples():
    frame = fruit_frame()
    original = frame.copy()
    segment = segment_guided(frame, (50, 20, 140, 140))
    assert segment.mask[90, 120] == 255
    assert segment.mask[30, 60] == 0
    assert not segment.touches_border
    assert np.array_equal(original, frame)
    _, snapshot = preview_frame(frame, {}, guided_segment=segment, frozen=True)
    assert snapshot['status'] == 'candidate'
    assert snapshot['frozen'] is True
    assert snapshot['segmentation_method'] == 'guided-grabcut'
    assert snapshot['species_verified'] is False
    assert snapshot['classification'] is None
    assert snapshot['metrics']['orange_color_ratio'] is None


@pytest.mark.parametrize(
    'rectangle', [None, (0, 0, 0, 0), (0, 5, 100, 100), (10, 10, 230, 100), (50, 50, -5, 20)]
)
def test_guided_selection_rejects_cancelled_or_out_of_bounds_rectangle(rectangle):
    with pytest.raises(VisionFailure):
        segment_guided(fruit_frame(), rectangle)


def test_guided_selection_does_not_apply_a_validated_hsv_classifier():
    class ForbiddenClassifier:
        def analyze(self, frame):
            pytest.fail('A seleção assistida não pode validar a classificação HSV.')

    frame = fruit_frame()
    segment = segment_guided(frame, (50, 20, 140, 140))
    _, state = preview_frame(
        frame, {'validated': True}, ForbiddenClassifier(), guided_segment=segment
    )
    assert state['classification'] is None
    assert state['visual_score'] is None


def test_grabcut_working_image_is_bounded_and_mask_returns_to_original_size(monkeypatch):
    seen = []

    def grabcut(image, labels, rectangle, background, foreground, iterations, mode):
        seen.append(image.shape)
        x, y, width, height = rectangle
        labels[y + 20 : y + height - 20, x + 20 : x + width - 20] = cv2.GC_PR_FGD

    monkeypatch.setattr(cv2, 'grabCut', grabcut)
    frame = np.zeros((1000, 2000, 3), dtype=np.uint8)
    result = segment_guided(frame, (200, 100, 1500, 800))
    assert seen == [(480, 960, 3)]
    assert result.mask.shape == frame.shape[:2]


def mock_windows(monkeypatch, keys):
    for name in (
        'namedWindow',
        'resizeWindow',
        'createTrackbar',
        'imshow',
        'destroyWindow',
        'destroyAllWindows',
    ):
        monkeypatch.setattr(cv2, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(cv2, 'getWindowProperty', lambda *args: 1)
    events = iter(keys)
    monkeypatch.setattr(cv2, 'waitKey', lambda _: next(events, ord('q')))
    monkeypatch.setattr(cv2, 'selectROI', lambda *args, **kwargs: (50, 20, 140, 140))


def test_freeze_selection_and_save_keep_same_camera_frame_until_resume(tmp_path, monkeypatch):
    first = fruit_frame()

    class Camera:
        calls = 0
        released = False

        def isOpened(self):
            return True

        def read(self):
            self.calls += 1
            return True, first.copy() if self.calls == 1 else np.zeros_like(first)

        def release(self):
            self.released = True

    camera = Camera()
    monkeypatch.setattr(cv2, 'VideoCapture', lambda _: camera)
    monkeypatch.setattr(cv2, 'getBuildInformation', lambda: 'GUI: WIN32UI')
    mock_windows(monkeypatch, [ord(' '), ord('b'), ord('s'), ord(' '), ord('q')])
    monkeypatch.setattr(sys, 'argv', ['lab', '--camera', '0', '--output', str(tmp_path)])
    lab.main()
    assert camera.calls == 2
    assert camera.released
    files = list(tmp_path.glob('captura-*.png'))
    assert len(files) == 1
    saved = cv2.imdecode(np.fromfile(str(files[0]), dtype=np.uint8), cv2.IMREAD_COLOR)
    assert np.array_equal(saved, first)


def test_switching_photo_discards_previous_guided_selection(tmp_path, monkeypatch, capsys):
    for name in ('one.png', 'two.png'):
        cv2.imencode('.png', fruit_frame())[1].tofile(str(tmp_path / name))
    monkeypatch.setattr(cv2, 'getBuildInformation', lambda: 'GUI: WIN32UI')
    mock_windows(monkeypatch, [ord('b'), ord('n'), ord('a'), ord('q')])
    monkeypatch.setattr(sys, 'argv', ['lab', '--images', str(tmp_path)])
    lab.main()
    states = [
        json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith('{')
    ]
    assert states[-1]['status'] == 'awaiting_sample'
    assert states[-1]['segmentation_method'] == 'hsv'
    assert states[-1]['classification'] is None
