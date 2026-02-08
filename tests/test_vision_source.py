"""Tests for VisionSource with optional YOLO classification."""

import unittest
from unittest.mock import MagicMock, patch

from cortex.sources.base import Event


class TestVisionSource(unittest.TestCase):
    """Test vision source motion detection and classification."""

    def setUp(self):
        try:
            import numpy as np
            self.np = np
        except ImportError:
            self.skipTest("numpy not available")

        from cortex.sources.vision import VisionSource
        self.VisionSource = VisionSource

    def _make_frame(self, value=128, shape=(240, 320, 3)):
        """Create a uniform test frame."""
        return self.np.full(shape, value, dtype=self.np.uint8)

    def test_name(self):
        source = self.VisionSource(lambda: None, classify=False)
        self.assertEqual(source.name, "vision")

    def test_first_frame_no_event(self):
        """First frame has nothing to compare with."""
        frame = self._make_frame(128)
        source = self.VisionSource(lambda: frame, classify=False)
        events = source.check()
        self.assertEqual(len(events), 0)

    def test_identical_frames_no_event(self):
        """Two identical frames should not trigger motion."""
        frame = self._make_frame(128)
        source = self.VisionSource(lambda: frame, classify=False)
        source.check()  # first frame
        events = source.check()  # same frame
        self.assertEqual(len(events), 0)

    def test_different_frames_trigger_motion(self):
        """Significantly different frames should trigger a motion event."""
        frames = [self._make_frame(50), self._make_frame(200)]
        idx = [0]
        def get_frame():
            f = frames[idx[0]]
            idx[0] = min(idx[0] + 1, len(frames) - 1)
            return f

        source = self.VisionSource(get_frame, classify=False, min_changed_ratio=0.01)
        source.check()  # first frame
        events = source.check()  # different frame
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "motion")
        self.assertEqual(events[0].source, "vision")
        self.assertIn("diff=", events[0].content)

    def test_none_frame_no_crash(self):
        """None frame should return empty list."""
        source = self.VisionSource(lambda: None, classify=False)
        events = source.check()
        self.assertEqual(len(events), 0)

    def test_exception_in_get_frame(self):
        """Exception in get_frame should return empty list."""
        def bad_frame():
            raise RuntimeError("camera error")

        source = self.VisionSource(bad_frame, classify=False)
        events = source.check()
        self.assertEqual(len(events), 0)

    def test_high_diff_gets_higher_priority(self):
        """Large pixel differences should get priority 7."""
        frames = [self._make_frame(0), self._make_frame(255)]
        idx = [0]
        def get_frame():
            f = frames[idx[0]]
            idx[0] = min(idx[0] + 1, len(frames) - 1)
            return f

        source = self.VisionSource(get_frame, classify=False, min_changed_ratio=0.01)
        source.check()
        events = source.check()
        self.assertEqual(events[0].priority, 7)

    def test_moderate_diff_gets_lower_priority(self):
        """Moderate pixel differences should get priority 4."""
        frames = [self._make_frame(100), self._make_frame(120)]
        idx = [0]
        def get_frame():
            f = frames[idx[0]]
            idx[0] = min(idx[0] + 1, len(frames) - 1)
            return f

        source = self.VisionSource(get_frame, classify=False, min_changed_ratio=0.01)
        source.check()
        events = source.check()
        if events:  # only if motion detected
            self.assertLessEqual(events[0].priority, 5)

    def test_grayscale_frame_works(self):
        """Should handle grayscale (2D) frames."""
        frames = [
            self.np.full((240, 320), 50, dtype=self.np.uint8),
            self.np.full((240, 320), 200, dtype=self.np.uint8),
        ]
        idx = [0]
        def get_frame():
            f = frames[idx[0]]
            idx[0] = min(idx[0] + 1, len(frames) - 1)
            return f

        source = self.VisionSource(get_frame, classify=False, min_changed_ratio=0.01)
        source.check()
        events = source.check()
        self.assertEqual(len(events), 1)

    def test_raw_data_contains_scores(self):
        """Motion events should contain diff_score and changed_ratio."""
        frames = [self._make_frame(50), self._make_frame(200)]
        idx = [0]
        def get_frame():
            f = frames[idx[0]]
            idx[0] = min(idx[0] + 1, len(frames) - 1)
            return f

        source = self.VisionSource(get_frame, classify=False, min_changed_ratio=0.01)
        source.check()
        events = source.check()
        self.assertIn("diff_score", events[0].raw_data)
        self.assertIn("changed_ratio", events[0].raw_data)

    def test_classify_disabled_no_yolo(self):
        """When classify=False, should not attempt YOLO."""
        frames = [self._make_frame(50), self._make_frame(200)]
        idx = [0]
        def get_frame():
            f = frames[idx[0]]
            idx[0] = min(idx[0] + 1, len(frames) - 1)
            return f

        source = self.VisionSource(get_frame, classify=False, min_changed_ratio=0.01)
        source.check()
        events = source.check()
        self.assertEqual(events[0].type, "motion")


class TestVisionSourceWithMockYOLO(unittest.TestCase):
    """Test YOLO classification path with mocked model."""

    def setUp(self):
        try:
            import numpy as np
            self.np = np
        except ImportError:
            self.skipTest("numpy not available")

    def _make_frame(self, value=128):
        return self.np.full((240, 320, 3), value, dtype=self.np.uint8)

    def _make_mock_result(self, class_ids, confidences):
        """Create a mock YOLO result."""
        result = MagicMock()
        boxes = []
        for cls_id, conf in zip(class_ids, confidences):
            box = MagicMock()
            box.cls = [cls_id]
            box.conf = [conf]
            boxes.append(box)
        result.boxes = boxes
        return result

    @patch("cortex.sources.vision.HAS_YOLO", True)
    def test_person_detection(self):
        """YOLO detecting person should create person event."""
        from cortex.sources.vision import VisionSource

        frames = [self._make_frame(50), self._make_frame(200)]
        idx = [0]
        def get_frame():
            f = frames[idx[0]]
            idx[0] = min(idx[0] + 1, len(frames) - 1)
            return f

        source = VisionSource(get_frame, min_changed_ratio=0.01, classify=True)
        source._classify = True  # force classify even if YOLO not installed

        mock_model = MagicMock()
        mock_model.return_value = [self._make_mock_result([0], [0.85])]
        source._model = mock_model

        source.check()  # first frame
        events = source.check()  # motion + classification

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "person")
        self.assertEqual(events[0].priority, 8)
        self.assertIn("person_count", events[0].raw_data)
        self.assertEqual(events[0].raw_data["person_count"], 1)

    @patch("cortex.sources.vision.HAS_YOLO", True)
    def test_animal_detection(self):
        """YOLO detecting cat should create animal event."""
        from cortex.sources.vision import VisionSource

        frames = [self._make_frame(50), self._make_frame(200)]
        idx = [0]
        def get_frame():
            f = frames[idx[0]]
            idx[0] = min(idx[0] + 1, len(frames) - 1)
            return f

        source = VisionSource(get_frame, min_changed_ratio=0.01, classify=True)
        source._classify = True

        mock_model = MagicMock()
        mock_model.return_value = [self._make_mock_result([15], [0.9])]
        source._model = mock_model

        source.check()
        events = source.check()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "animal")
        self.assertEqual(events[0].priority, 3)
        self.assertIn("cat", events[0].content)

    @patch("cortex.sources.vision.HAS_YOLO", True)
    def test_no_relevant_detection_falls_back_to_motion(self):
        """YOLO detecting nothing relevant should fall back to motion."""
        from cortex.sources.vision import VisionSource

        frames = [self._make_frame(50), self._make_frame(200)]
        idx = [0]
        def get_frame():
            f = frames[idx[0]]
            idx[0] = min(idx[0] + 1, len(frames) - 1)
            return f

        source = VisionSource(get_frame, min_changed_ratio=0.01, classify=True)
        source._classify = True

        mock_model = MagicMock()
        # class 56 = chair — not in our COCO_LABELS
        mock_model.return_value = [self._make_mock_result([56], [0.7])]
        source._model = mock_model

        source.check()
        events = source.check()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "motion")

    @patch("cortex.sources.vision.HAS_YOLO", True)
    def test_person_priority_over_animal(self):
        """When both person and animal detected, person event takes priority."""
        from cortex.sources.vision import VisionSource

        frames = [self._make_frame(50), self._make_frame(200)]
        idx = [0]
        def get_frame():
            f = frames[idx[0]]
            idx[0] = min(idx[0] + 1, len(frames) - 1)
            return f

        source = VisionSource(get_frame, min_changed_ratio=0.01, classify=True)
        source._classify = True

        mock_model = MagicMock()
        # person + dog
        mock_model.return_value = [self._make_mock_result([0, 16], [0.9, 0.8])]
        source._model = mock_model

        source.check()
        events = source.check()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "person")


if __name__ == "__main__":
    unittest.main()
