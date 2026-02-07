"""Decision engine for choosing actions based on events.

Routes incoming events to appropriate actions and selects autonomous
activities when idle. Activities and event handlers are fully pluggable.
"""

import random
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any

from .defaults import AUTONOMOUS_ACTIVITIES


@dataclass
class Action:
    """An action to be executed by the agent."""
    name: str
    description: str
    params: dict = None
    handler: Optional[Callable] = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}

    def execute(self) -> Dict[str, Any]:
        """Execute this action's handler if one is set."""
        if self.handler:
            try:
                result = self.handler(**self.params)
                return {"status": "ok", "action": self.name, "result": result}
            except Exception as e:
                return {"status": "error", "action": self.name, "error": str(e)}
        return {"status": "ok", "action": self.name}


class DecisionEngine:
    """Decides what action to take based on incoming events.

    Args:
        activities: List of dicts with keys 'name', 'description', 'weight'.
            Used for weighted random selection during idle periods.
        event_handlers: Dict mapping (source, condition) to handler functions.
            Each handler receives an event and returns an Action.
    """

    def __init__(
        self,
        activities: Optional[List[Dict[str, Any]]] = None,
        event_handlers: Optional[Dict[str, Callable]] = None,
    ):
        self.activities = activities or AUTONOMOUS_ACTIVITIES
        self.event_handlers = event_handlers or {}

    def decide(self, events: list) -> Action:
        """Choose the best action given a list of events.

        Args:
            events: List of Event objects (from sources.base).

        Returns:
            An Action to execute.
        """
        if not events:
            return self.choose_autonomous_activity()

        # Sort by priority (highest first)
        sorted_events = sorted(events, key=lambda e: e.priority, reverse=True)
        top = sorted_events[0]

        # Check registered event handlers
        handler = self.event_handlers.get(top.source)
        if handler:
            return handler(top)

        # Default: generic event processing
        return Action(
            "process_event",
            f"Process event from {top.source}: {top.content[:80]}",
            {"event": top},
        )

    def choose_autonomous_activity(self) -> Action:
        """Select a random autonomous activity using weighted selection."""
        names = [a["name"] for a in self.activities]
        descriptions = [a["description"] for a in self.activities]
        weights = [a.get("weight", 1.0) for a in self.activities]

        chosen = random.choices(range(len(self.activities)), weights=weights)[0]
        return Action(names[chosen], descriptions[chosen])
