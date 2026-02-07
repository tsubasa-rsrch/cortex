"""Base classes for event sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Event:
    """An event from an input source."""
    source: str           # Source name
    type: str             # Event type (mention, reply, message, motion, etc.)
    content: str          # Content text
    author: Optional[str] = None  # Author if applicable
    url: Optional[str] = None     # URL if applicable
    timestamp: datetime = None    # When the event occurred
    priority: int = 5             # Priority 1-10 (higher = more important)
    raw_data: dict = None         # Raw source data

    def __post_init__(self):
        if self.raw_data is None:
            self.raw_data = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BaseSource(ABC):
    """Abstract base class for input sources.

    Subclass this to create custom event sources (e.g., camera, messaging, API).
    """

    def __init__(self, config=None):
        self.config = config
        self._last_check = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Source name identifier."""
        pass

    @abstractmethod
    def check(self) -> List[Event]:
        """Check for new events and return a list."""
        pass

    def _mark_checked(self):
        """Record check timestamp."""
        self._last_check = datetime.now()
