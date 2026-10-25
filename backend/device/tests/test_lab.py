import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from backend.device.lab import edited, image_paths, sample_range, save_draft, source_rectangle


class LabTests(unittest.TestCase):
    def test_saved_draft_is_never_validated_and_does_not_overwrite_previous(self):
        with tempfile.TemporaryDirectory() as directory:
            calibration = {'validated': True, 'fruit_hsv': [[[10, 100, 100], [30, 255, 255]]]}
            first = save_draft(calibration, directory)
            second = save_draft(calibration, directory)
            self.assertNotEqual(first, second)
            self.assertFalse(json.loads(first.read_text(encoding='utf-8'))['validated'])
            self.assertTrue(calibration['validated'])

    def test_selection_on_thumbnail_maps_back_to_source_pixels(self):
        self.assertEqual(
            source_rectangle((10, 20, 30, 40), (1200, 1800, 3), (400, 600, 3)), (30, 60, 90, 120)
        )
        self.assertEqual(
            source_rectangle((0, 0, 0, 0), (1200, 1800, 3), (400, 600, 3)), (0, 0, 0, 0)
        )

    def test_edit_invalidates_validated_calibration(self):
        calibration = {'validated': True, 'version': 'approved-version'}
        edited(calibration)
        self.assertFalse(calibration['validated'])
        self.assertTrue(calibration['version'].startswith('rascunho-'))

    def test_sample_uses_selected_region_not_background(self):
        hsv = np.zeros((20, 20, 3), dtype=np.uint8)
        hsv[5:15, 5:15] = (20, 180, 200)
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        lower, upper = sample_range(frame, (5, 5, 10, 10))
        self.assertTrue(19 <= lower[0] <= upper[0] <= 21)
        self.assertGreater(lower[1], 170)

    def test_cancelled_selection_is_not_a_sample(self):
        with self.assertRaises(ValueError):
            sample_range(np.zeros((10, 10, 3), dtype=np.uint8), (0, 0, 0, 0))

    def test_dataset_includes_nested_images_not_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'classe').mkdir()
            image = base / 'classe' / 'foto.PNG'
            image.touch()
            (base / 'labels.csv').touch()
            self.assertEqual(image_paths(base), [image])


if __name__ == '__main__':
    unittest.main()
