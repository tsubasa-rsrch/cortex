"""Tests for ReachyMini event sources."""

import math
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from cortex.sources.base import Event


class MockReachyMini:
    """Mock ReachyMini for testing without hardware."""

    def __init__(self):
        self.media = MagicMock()
        self._imu_data = None

    @property
    def imu(self):
        return self._imu_data


class TestReachyCameraSource(unittest.TestCase):
    """Test camera-based motion detection."""

    def setUp(self):
        try:
            import numpy as np
            self.np = np
        except ImportError:
            self.skipTest("numpy not available")

        from cortex.sources.reachy import ReachyCameraSource
        self.mini = MockReachyMini()
        self.source = ReachyCameraSource(self.mini, diff_threshold=15.0, min_changed_ratio=0.05)

    def test_name(self):
        self.assertEqual(self.source.name, "reachy_camera")

    def test_first_frame_no_event(self):
        """First frame has nothing to compare to."""
        frame = self.np.zeros((120, 160, 3), dtype=self.np.uint8)
        self.mini.media.get_frame.return_value = frame
        events = self.source.check()
        self.assertEqual(events, [])

    def test_no_motion(self):
        """Same frame twice = no motion."""
        frame = self.np.ones((120, 160, 3), dtype=self.np.uint8) * 128
        self.mini.media.get_frame.return_value = frame
        self.source.check()  # first frame
        events = self.source.check()  # same frame
        self.assertEqual(events, [])

    def test_motion_detected(self):
        """Large change between frames triggers event."""
        frame1 = self.np.zeros((120, 160, 3), dtype=self.np.uint8)
        frame2 = self.np.ones((120, 160, 3), dtype=self.np.uint8) * 200
        self.mini.media.get_frame.side_effect = [frame1, frame2]
        self.source.check()  # first frame
        events = self.source.check()  # different frame
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].source, "motion")
        self.assertEqual(events[0].type, "motion")
        self.assertIn("diff_score", events[0].raw_data)

    def test_high_diff_high_priority(self):
        """Very high diff gets priority 7."""
        frame1 = self.np.zeros((120, 160, 3), dtype=self.np.uint8)
        frame2 = self.np.ones((120, 160, 3), dtype=self.np.uint8) * 255
        self.mini.media.get_frame.side_effect = [frame1, frame2]
        self.source.check()
        events = self.source.check()
        self.assertEqual(events[0].priority, 7)

    def test_get_frame_error_graceful(self):
        """Error in get_frame disables source gracefully."""
        self.mini.media.get_frame.side_effect = RuntimeError("no camera")
        events = self.source.check()
        self.assertEqual(events, [])
        self.assertFalse(self.source._available)

    def test_none_frame_ignored(self):
        """None frame returns no events."""
        self.mini.media.get_frame.return_value = None
        events = self.source.check()
        self.assertEqual(events, [])


class TestReachyAudioSource(unittest.TestCase):
    """Test audio/speech detection."""

    def setUp(self):
        try:
            import numpy as np
            self.np = np
        except ImportError:
            self.skipTest("numpy not available")

        from cortex.sources.reachy import ReachyAudioSource
        self.mini = MockReachyMini()
        self.source = ReachyAudioSource(self.mini, energy_threshold=0.01)

    def test_name(self):
        self.assertEqual(self.source.name, "reachy_audio")

    def test_speech_detected(self):
        """DoA returns speech = voice event."""
        self.mini.media.get_DoA.return_value = (math.radians(90), True)
        self.mini.media.get_audio_sample.return_value = None
        events = self.source.check()
        speech_events = [e for e in events if e.type == "speech"]
        self.assertEqual(len(speech_events), 1)
        self.assertEqual(speech_events[0].source, "voice")
        self.assertEqual(speech_events[0].raw_data["direction"], "left")

    def test_no_speech(self):
        """DoA with no speech = no voice event."""
        self.mini.media.get_DoA.return_value = (0.0, False)
        self.mini.media.get_audio_sample.return_value = None
        events = self.source.check()
        speech_events = [e for e in events if e.type == "speech"]
        self.assertEqual(len(speech_events), 0)

    def test_loud_sound(self):
        """High energy audio = sound event."""
        self.mini.media.get_DoA.return_value = None
        loud_audio = self.np.ones(16000, dtype=self.np.float32) * 0.5
        self.mini.media.get_audio_sample.return_value = loud_audio
        events = self.source.check()
        sound_events = [e for e in events if e.type == "sound"]
        self.assertEqual(len(sound_events), 1)
        self.assertGreater(sound_events[0].raw_data["rms_energy"], 0.01)

    def test_quiet_audio(self):
        """Low energy audio = no sound event."""
        self.mini.media.get_DoA.return_value = None
        quiet = self.np.ones(16000, dtype=self.np.float32) * 0.001
        self.mini.media.get_audio_sample.return_value = quiet
        events = self.source.check()
        sound_events = [e for e in events if e.type == "sound"]
        self.assertEqual(len(sound_events), 0)

    def test_direction_mapping(self):
        """Verify angle-to-direction mapping."""
        from cortex.sources.reachy import ReachyAudioSource
        self.assertEqual(ReachyAudioSource._angle_to_direction(0), "front")
        self.assertEqual(ReachyAudioSource._angle_to_direction(90), "left")
        self.assertEqual(ReachyAudioSource._angle_to_direction(180), "back")
        self.assertEqual(ReachyAudioSource._angle_to_direction(270), "right")
        self.assertEqual(ReachyAudioSource._angle_to_direction(350), "front")


class TestReachyIMUSource(unittest.TestCase):
    """Test IMU bump detection."""

    def setUp(self):
        from cortex.sources.reachy import ReachyIMUSource
        self.mini = MockReachyMini()
        self.source = ReachyIMUSource(self.mini, accel_threshold=2.0)

    def test_name(self):
        self.assertEqual(self.source.name, "reachy_imu")

    def test_first_reading_no_event(self):
        """First reading has nothing to compare to."""
        self.mini._imu_data = {"accelerometer": [0, 0, 9.8]}
        events = self.source.check()
        self.assertEqual(events, [])

    def test_no_bump(self):
        """Stable readings = no event."""
        self.mini._imu_data = {"accelerometer": [0, 0, 9.8]}
        self.source.check()  # baseline
        self.mini._imu_data = {"accelerometer": [0.1, 0, 9.7]}
        events = self.source.check()
        self.assertEqual(events, [])

    def test_bump_detected(self):
        """Sudden accel change = bump event."""
        self.mini._imu_data = {"accelerometer": [0, 0, 9.8]}
        self.source.check()  # baseline
        self.mini._imu_data = {"accelerometer": [5, 5, 12.0]}
        events = self.source.check()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].source, "imu")
        self.assertEqual(events[0].type, "bump")
        self.assertEqual(events[0].priority, 8)

    def test_imu_none(self):
        """IMU returns None = no event."""
        self.mini._imu_data = None
        events = self.source.check()
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
