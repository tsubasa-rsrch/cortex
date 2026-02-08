"""General-purpose vision source with optional YOLO classification.

Works with any camera that can provide frames as numpy arrays.
Combines motion detection (frame differencing) with optional
object classification (YOLO) for richer perception events.

When YOLO is available:
    Motion detected → classify → person/animal/other events
When YOLO is not available:
    Motion detected → generic motion events

Usage:
    # With ReachyMini
    source = VisionSource(mini.media.get_frame)

    # With any camera
    source = VisionSource(my_camera_fn, diff_threshold=20.0)

    events = source.check()
"""

import math
from typing import Callable, List, Optional
from datetime import datetime

from .base import Event, BaseSource

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# YOLO is optional — works without it (motion-only mode)
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False

# COCO class IDs for person and common animals
PERSON_CLASSES = {0}
ANIMAL_CLASSES = {14, 15, 16}  # bird, cat, dog

COCO_LABELS = {
    0: "person",
    14: "bird",
    15: "cat",
    16: "dog",
}


class VisionSource(BaseSource):
    """Vision source with motion detection and optional YOLO classification.

    Args:
        get_frame: Callable that returns a numpy array (H, W, 3) or None.
        diff_threshold: Pixel difference threshold for motion detection.
        min_changed_ratio: Minimum ratio of changed pixels to trigger.
        yolo_confidence: YOLO detection confidence threshold.
        classify: Whether to run YOLO classification on motion frames.
    """

    def __init__(
        self,
        get_frame: Callable[[], Optional["np.ndarray"]],
        diff_threshold: float = 15.0,
        min_changed_ratio: float = 0.0668,
        yolo_confidence: float = 0.35,
        classify: bool = True,
    ):
        super().__init__()
        self._get_frame = get_frame
        self.diff_threshold = diff_threshold
        self.min_changed_ratio = min_changed_ratio
        self.yolo_confidence = yolo_confidence
        self._classify = classify and HAS_YOLO
        self._prev_frame = None
        self._model = None

    @property
    def name(self) -> str:
        return "vision"

    def check(self) -> List[Event]:
        """Capture frame, detect motion, optionally classify."""
        if not HAS_NUMPY:
            return []

        try:
            frame = self._get_frame()
        except Exception:
            return []

        if frame is None:
            return []

        # Convert to grayscale for motion detection
        if len(frame.shape) == 3:
            gray = np.mean(frame, axis=2).astype(np.uint8)
        else:
            gray = frame

        events = []
        motion_detected = False
        diff_score = 0.0
        changed_ratio = 0.0

        if self._prev_frame is not None:
            diff = np.abs(gray.astype(float) - self._prev_frame.astype(float))
            diff_score = float(np.mean(diff))
            changed_ratio = float(np.mean(diff > self.diff_threshold))
            motion_detected = changed_ratio >= self.min_changed_ratio

        self._prev_frame = gray

        if not motion_detected:
            self._mark_checked()
            return []

        # Motion detected — classify if YOLO available
        if self._classify:
            events = self._classify_frame(frame, diff_score, changed_ratio)
        else:
            # Fallback: generic motion event
            priority = 7 if diff_score > 30 else 4
            events.append(Event(
                source="vision",
                type="motion",
                content=f"Motion detected (diff={diff_score:.1f})",
                priority=priority,
                raw_data={
                    "diff_score": diff_score,
                    "changed_ratio": changed_ratio,
                },
            ))

        self._mark_checked()
        return events

    def _classify_frame(
        self, frame: "np.ndarray", diff_score: float, changed_ratio: float
    ) -> List[Event]:
        """Run YOLO classification on a frame."""
        if self._model is None:
            try:
                self._model = YOLO("yolov8n.pt")
            except Exception:
                # Fallback to motion-only
                return [Event(
                    source="vision",
                    type="motion",
                    content=f"Motion detected (diff={diff_score:.1f})",
                    priority=5,
                    raw_data={"diff_score": diff_score, "changed_ratio": changed_ratio},
                )]

        try:
            results = self._model(frame, conf=self.yolo_confidence, verbose=False)
        except Exception:
            return [Event(
                source="vision",
                type="motion",
                content=f"Motion detected (diff={diff_score:.1f})",
                priority=5,
                raw_data={"diff_score": diff_score, "changed_ratio": changed_ratio},
            )]

        person_count = 0
        animal_count = 0
        detections = []

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                label = COCO_LABELS.get(cls_id)
                if label is None:
                    continue
                detections.append({"label": label, "confidence": conf, "class_id": cls_id})
                if cls_id in PERSON_CLASSES:
                    person_count += 1
                elif cls_id in ANIMAL_CLASSES:
                    animal_count += 1

        events = []

        if person_count > 0:
            events.append(Event(
                source="vision",
                type="person",
                content=f"{person_count} person(s) detected (diff={diff_score:.1f})",
                priority=8,
                raw_data={
                    "person_count": person_count,
                    "animal_count": animal_count,
                    "detections": detections,
                    "diff_score": diff_score,
                    "changed_ratio": changed_ratio,
                },
            ))
        elif animal_count > 0:
            labels = [d["label"] for d in detections if d["class_id"] in ANIMAL_CLASSES]
            events.append(Event(
                source="vision",
                type="animal",
                content=f"{', '.join(labels)} detected (diff={diff_score:.1f})",
                priority=3,
                raw_data={
                    "person_count": person_count,
                    "animal_count": animal_count,
                    "detections": detections,
                    "diff_score": diff_score,
                    "changed_ratio": changed_ratio,
                },
            ))
        else:
            events.append(Event(
                source="vision",
                type="motion",
                content=f"Motion detected (diff={diff_score:.1f})",
                priority=5,
                raw_data={
                    "diff_score": diff_score,
                    "changed_ratio": changed_ratio,
                    "detections": detections,
                },
            ))

        return events
