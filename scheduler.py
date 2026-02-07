"""Task scheduler for periodic operations.

Register callbacks with intervals, and the scheduler handles timing,
state persistence, and execution. Inspired by cron but for in-process use.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Any, Optional

from .config import get_config

STATE_FILENAME = "scheduler_state.json"


class ScheduledTask:
    """A single scheduled task."""

    def __init__(
        self,
        name: str,
        interval_seconds: int,
        callback: Callable[[], Any],
        enabled: bool = True,
        description: str = "",
    ):
        self.name = name
        self.interval_seconds = interval_seconds
        self.callback = callback
        self.enabled = enabled
        self.description = description
        self.last_run: Optional[float] = None

    def should_run(self) -> bool:
        """Check if this task is due to run."""
        if not self.enabled:
            return False
        if self.last_run is None:
            return True
        return (time.time() - self.last_run) >= self.interval_seconds

    def run(self) -> Dict[str, Any]:
        """Execute the task callback."""
        try:
            result = self.callback()
            self.last_run = time.time()
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def time_until_next(self) -> float:
        """Seconds remaining until next scheduled run."""
        if self.last_run is None:
            return 0
        remaining = self.interval_seconds - (time.time() - self.last_run)
        return max(0, remaining)


class Scheduler:
    """Task scheduler with persistent state.

    Args:
        config: Optional CortexConfig. Uses global config if not provided.
    """

    def __init__(self, config=None):
        self._config = config or get_config()
        self._state_file = self._config.state_file(STATE_FILENAME)
        self.tasks: Dict[str, ScheduledTask] = {}
        self._saved_state: Dict = {}
        self._load_state()

    def register(
        self,
        name: str,
        interval_seconds: int,
        callback: Callable[[], Any],
        enabled: bool = True,
        description: str = "",
    ) -> None:
        """Register a periodic task."""
        task = ScheduledTask(
            name=name,
            interval_seconds=interval_seconds,
            callback=callback,
            enabled=enabled,
            description=description,
        )
        if name in self._saved_state:
            task.last_run = self._saved_state[name].get("last_run")
        self.tasks[name] = task

    def unregister(self, name: str) -> bool:
        """Remove a registered task."""
        if name in self.tasks:
            del self.tasks[name]
            return True
        return False

    def enable(self, name: str) -> bool:
        """Enable a task by name."""
        if name in self.tasks:
            self.tasks[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a task by name."""
        if name in self.tasks:
            self.tasks[name].enabled = False
            return True
        return False

    def check_and_run(self) -> Dict[str, Any]:
        """Check all tasks and run any that are due."""
        results = {}
        for name, task in self.tasks.items():
            if task.should_run():
                results[name] = task.run()
        if results:
            self._save_state()
        return results

    def get_status(self) -> Dict[str, Dict]:
        """Get status of all registered tasks."""
        status = {}
        for name, task in self.tasks.items():
            status[name] = {
                "enabled": task.enabled,
                "interval_seconds": task.interval_seconds,
                "interval_human": _format_interval(task.interval_seconds),
                "description": task.description,
                "last_run": (
                    datetime.fromtimestamp(task.last_run).isoformat()
                    if task.last_run
                    else None
                ),
                "next_in_seconds": task.time_until_next(),
                "next_in_human": _format_interval(int(task.time_until_next())),
            }
        return status

    def _load_state(self) -> None:
        if self._state_file.exists():
            try:
                with open(self._state_file, "r") as f:
                    self._saved_state = json.load(f)
            except Exception:
                self._saved_state = {}

    def _save_state(self) -> None:
        state = {}
        for name, task in self.tasks.items():
            state[name] = {"last_run": task.last_run, "enabled": task.enabled}
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass


def _format_interval(seconds: int) -> str:
    """Format seconds into a human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    else:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h{m}m" if m else f"{h}h"
