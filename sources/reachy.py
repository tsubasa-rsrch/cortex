"""ReachyMini event sources for Cortex.

Provides BaseSource implementations that bridge ReachyMini's sensors
into Cortex's event pipeline:
  - ReachyCameraSource: Motion detection via frame differencing
  - ReachyAudioSource: Sound/speech detection via mic array + DoA
  - ReachyIMUSource: Sudden movement detection via accelerometer

Requires: reachy-mini SDK (pip install reachy-mini)

Usage:
    from cortex.sources.reachy import ReachyCameraSource, ReachyAudioSource

    camera = ReachyCameraSource(mini)
    events = camera.check()  # Returns motion events if detected
"""

import math
from typing import List, Optional
from datetime import datetime

from .base import Event, BaseSource

# numpy is required for frame processing but may not be installed
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class ReachyCameraSource(BaseSource):
    """Detects motion via frame differencing on ReachyMini's camera.

    Compares consecutive frames and generates events when the
    difference exceeds a threshold — same principle as the
    tsubasa-daemon's prediction-error detection system.

    Args:
        mini: Connected ReachyMini instance.
        diff_threshold: Minimum mean pixel difference to trigger (0-255).
        min_changed_ratio: Minimum ratio of changed pixels (0.0-1.0).
    """

    def __init__(self, mini, diff_threshold: float = 15.0,
                 min_changed_ratio: float = 0.0668):
        super().__init__()
        self.mini = mini
        self.diff_threshold = diff_threshold
        self.min_changed_ratio = min_changed_ratio
        self._prev_frame = None
        self._available = True

    @property
    def name(self) -> str:
        return "reachy_camera"

    def check(self) -> List[Event]:
        """Capture a frame and compare with previous."""
        if not self._available or not HAS_NUMPY:
            return []

        try:
            frame = self.mini.media.get_frame()
        except Exception:
            self._available = False
            return []

        if frame is None:
            return []

        # Convert to grayscale for comparison
        if len(frame.shape) == 3:
            gray = np.mean(frame, axis=2).astype(np.uint8)
        else:
            gray = frame

        events = []
        if self._prev_frame is not None:
            diff = np.abs(gray.astype(float) - self._prev_frame.astype(float))
            mean_diff = float(np.mean(diff))
            changed_ratio = float(np.mean(diff > self.diff_threshold))

            if changed_ratio >= self.min_changed_ratio:
                priority = 7 if mean_diff > 30 else 4
                events.append(Event(
                    source="motion",
                    type="motion",
                    content=f"Motion detected (diff={mean_diff:.1f}, changed={changed_ratio:.3f})",
                    priority=priority,
                    raw_data={
                        "diff_score": mean_diff,
                        "changed_ratio": changed_ratio,
                        "frame_shape": list(frame.shape),
                    },
                ))

        self._prev_frame = gray
        self._mark_checked()
        return events


class ReachyAudioSource(BaseSource):
    """Detects sound and speech via ReachyMini's 4-mic array.

    Uses get_DoA() for speech detection and direction,
    and get_audio_sample() for general sound level monitoring.

    Args:
        mini: Connected ReachyMini instance.
        energy_threshold: Minimum RMS energy to trigger sound event.
    """

    def __init__(self, mini, energy_threshold: float = 0.01):
        super().__init__()
        self.mini = mini
        self.energy_threshold = energy_threshold
        self._available = True

    @property
    def name(self) -> str:
        return "reachy_audio"

    def check(self) -> List[Event]:
        """Check for speech/sound events."""
        if not self._available or not HAS_NUMPY:
            return []

        events = []

        # Check Direction of Arrival (speech detection)
        try:
            doa_result = self.mini.media.get_DoA()
            if doa_result is not None:
                doa_rad, is_speech = doa_result
                if is_speech:
                    doa_deg = math.degrees(doa_rad)
                    # Map angle to direction
                    direction = self._angle_to_direction(doa_deg)
                    events.append(Event(
                        source="voice",
                        type="speech",
                        content=f"Speech detected from {direction} ({doa_deg:.0f} deg)",
                        priority=6,
                        raw_data={
                            "doa_radians": doa_rad,
                            "doa_degrees": doa_deg,
                            "direction": direction,
                            "is_speech": True,
                        },
                    ))
        except Exception:
            pass

        # Check audio energy level
        try:
            audio = self.mini.media.get_audio_sample()
            if audio is not None and HAS_NUMPY:
                rms = float(np.sqrt(np.mean(audio ** 2)))
                if rms > self.energy_threshold:
                    events.append(Event(
                        source="audio",
                        type="sound",
                        content=f"Sound detected (rms={rms:.4f})",
                        priority=3,
                        raw_data={
                            "rms_energy": rms,
                            "peak": float(np.max(np.abs(audio))),
                            "samples": len(audio),
                        },
                    ))
        except Exception:
            pass

        self._mark_checked()
        return events

    @staticmethod
    def _angle_to_direction(degrees: float) -> str:
        """Convert DoA angle to human-readable direction."""
        # Normalize to 0-360
        d = degrees % 360
        if d < 45 or d >= 315:
            return "front"
        elif d < 135:
            return "left"
        elif d < 225:
            return "back"
        else:
            return "right"


class ReachyIMUSource(BaseSource):
    """Detects sudden movements via ReachyMini's IMU (wireless version only).

    Monitors accelerometer data for sudden changes that indicate
    the robot has been bumped, picked up, or moved.

    Args:
        mini: Connected ReachyMini instance.
        accel_threshold: Minimum acceleration magnitude change to trigger.
    """

    def __init__(self, mini, accel_threshold: float = 2.0):
        super().__init__()
        self.mini = mini
        self.accel_threshold = accel_threshold
        self._prev_accel_mag = None
        self._available = True

    @property
    def name(self) -> str:
        return "reachy_imu"

    def check(self) -> List[Event]:
        """Check IMU for sudden movement."""
        if not self._available:
            return []

        try:
            imu_data = self.mini.imu
        except Exception:
            self._available = False
            return []

        if imu_data is None:
            return []

        events = []
        accel = imu_data.get("accelerometer", [0, 0, 0])
        if isinstance(accel, list) and len(accel) >= 3:
            mag = math.sqrt(sum(a ** 2 for a in accel))

            if self._prev_accel_mag is not None:
                delta = abs(mag - self._prev_accel_mag)
                if delta > self.accel_threshold:
                    events.append(Event(
                        source="imu",
                        type="bump",
                        content=f"Sudden movement detected (delta={delta:.2f}g)",
                        priority=8,
                        raw_data={
                            "accelerometer": accel,
                            "magnitude": mag,
                            "delta": delta,
                            "gyroscope": imu_data.get("gyroscope"),
                            "temperature": imu_data.get("temperature"),
                        },
                    ))

            self._prev_accel_mag = mag

        self._mark_checked()
        return events
