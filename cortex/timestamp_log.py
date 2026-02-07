"""Timestamp logger for tracking task durations.

Helps agents maintain accurate time perception by recording
task start/end times and checkpoints. Prevents time-drift
during long autonomous sessions.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .config import get_config

STATE_FILENAME = "timestamp_log.json"


class TimestampLog:
    """Tracks task timing with checkpoints.

    Args:
        config: Optional CortexConfig. Uses global config if not provided.
    """

    def __init__(self, config=None):
        self._config = config or get_config()
        self._log_file = self._config.state_file(STATE_FILENAME)
        self._data = self._load()

    def start_task(self, task_name: str) -> Dict[str, Any]:
        """Record the start of a task. Auto-ends any running task.

        Returns:
            Dict with task name and start time.
        """
        now = datetime.now()

        if self._data["current_task"]:
            self.end_task("(auto-ended)")

        self._data["current_task"] = {
            "name": task_name,
            "started": now.isoformat(),
            "checkpoints": [],
        }
        self._data["entries"].append({
            "type": "start",
            "task": task_name,
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        })
        self._save()
        return {"task": task_name, "started": now.strftime("%H:%M:%S")}

    def checkpoint(self, note: str = "") -> Optional[Dict[str, Any]]:
        """Record a checkpoint on the current task.

        Returns:
            Dict with task name, elapsed minutes, and note. None if no task.
        """
        if not self._data["current_task"]:
            return None

        now = datetime.now()
        started = datetime.fromisoformat(self._data["current_task"]["started"])
        elapsed_min = int((now - started).total_seconds() / 60)

        self._data["current_task"]["checkpoints"].append({
            "time": now.isoformat(),
            "elapsed_min": elapsed_min,
            "note": note,
        })
        self._save()
        return {
            "task": self._data["current_task"]["name"],
            "elapsed_min": elapsed_min,
            "note": note,
        }

    def end_task(self, note: str = "") -> Optional[Dict[str, Any]]:
        """End the current task.

        Returns:
            Dict with task summary. None if no task.
        """
        if not self._data["current_task"]:
            return None

        now = datetime.now()
        started = datetime.fromisoformat(self._data["current_task"]["started"])
        elapsed_min = int((now - started).total_seconds() / 60)
        task_name = self._data["current_task"]["name"]
        num_checkpoints = len(self._data["current_task"]["checkpoints"])

        self._data["entries"].append({
            "type": "end",
            "task": task_name,
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_min": elapsed_min,
            "checkpoints": num_checkpoints,
            "note": note,
        })
        self._data["current_task"] = None
        self._save()
        return {
            "task": task_name,
            "elapsed_min": elapsed_min,
            "checkpoints": num_checkpoints,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current status including active task and recent entries."""
        now = datetime.now()
        status: Dict[str, Any] = {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "current_task": None,
            "recent_entries": self._data["entries"][-5:],
        }

        if self._data["current_task"]:
            started = datetime.fromisoformat(self._data["current_task"]["started"])
            elapsed_min = int((now - started).total_seconds() / 60)
            status["current_task"] = {
                "name": self._data["current_task"]["name"],
                "started": started.strftime("%H:%M:%S"),
                "elapsed_min": elapsed_min,
            }

        return status

    def _load(self) -> Dict:
        if self._log_file.exists():
            try:
                return json.loads(self._log_file.read_text())
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {"entries": [], "current_task": None}

    def _save(self) -> None:
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        self._log_file.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False)
        )
