"""Habituation filter based on cognitive science.

Implements three key mechanisms from human attention:
- Habituation: Repeated stimuli from the same source reduce sensitivity.
- Orienting response: Abnormally large stimuli always trigger notification.
- Cooldown: Prevents rapid-fire notifications from the same source.
"""

from collections import defaultdict, deque
from time import time


class HabituationFilter:
    """Cognitive-science-based notification filter.

    Args:
        cooldown: Minimum seconds between notifications from the same source.
        window: Time window (seconds) for habituation counting.
        habituate_count: Number of detections in window to trigger habituation.
        habituated_mult: Threshold multiplier when habituated.
        orienting_mult: Threshold multiplier for orienting response (always notifies).
        base_threshold: Base detection threshold.
    """

    def __init__(
        self,
        cooldown: float = 60.0,
        window: float = 300.0,
        habituate_count: int = 3,
        habituated_mult: float = 2.0,
        orienting_mult: float = 2.0,
        base_threshold: float = 15.0,
    ):
        self.cooldown = cooldown
        self.window = window
        self.habituate_count = habituate_count
        self.habituated_mult = habituated_mult
        self.orienting_mult = orienting_mult
        self.base_threshold = base_threshold
        self.history = defaultdict(deque)
        self.last_notify = {}

    def should_notify(self, source: str, value: float) -> tuple:
        """Determine whether a stimulus should trigger a notification.

        Args:
            source: Source identifier (e.g., camera name, sensor ID).
            value: Stimulus magnitude (e.g., image diff score).

        Returns:
            Tuple of (should_notify: bool, reason: str).
        """
        now = time()

        # Orienting response: abnormally large stimulus always notifies
        orienting_threshold = self.base_threshold * self.orienting_mult
        if value >= orienting_threshold:
            self.last_notify[source] = now
            self._record(source, now)
            return True, f"Orienting response (value={value:.1f} >= {orienting_threshold:.1f})"

        # Cooldown check
        last = self.last_notify.get(source, 0)
        if now - last < self.cooldown:
            self._record(source, now)
            return False, f"Cooldown ({now - last:.0f}s < {self.cooldown:.0f}s)"

        # Prune old history
        self._prune(source, now)

        # Habituation check
        threshold = self.base_threshold
        habituated = len(self.history[source]) >= self.habituate_count
        if habituated:
            threshold *= self.habituated_mult

        if value >= threshold:
            self.last_notify[source] = now
            self._record(source, now)
            state = "habituated" if habituated else "alert"
            return True, f"Motion ({state}, value={value:.1f} >= threshold={threshold:.1f})"

        self._record(source, now)
        return False, f"Below threshold ({value:.1f} < {threshold:.1f})"

    def _record(self, source: str, now: float):
        self.history[source].append(now)

    def _prune(self, source: str, now: float):
        q = self.history[source]
        cutoff = now - self.window
        while q and q[0] < cutoff:
            q.popleft()
