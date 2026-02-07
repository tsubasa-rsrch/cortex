"""Notification queue for agent communication.

File-based notification system that allows background processes to
send notifications to the agent. Non-destructive: notifications persist
until explicitly marked as read.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .config import get_config
from .defaults import NOTIFICATION_ICONS, PRIORITY_MARKS


class NotificationQueue:
    """File-based notification queue.

    Args:
        config: Optional CortexConfig. Uses global config if not provided.
        notification_dir: Override directory for notification files.
            Defaults to a 'notifications' subdirectory in config.data_dir.
        icons: Dict mapping notification types to icon strings.
        priority_marks: Dict mapping priority levels to marker strings.
        max_queue: Maximum number of notifications to retain.
    """

    def __init__(
        self,
        config=None,
        notification_dir: Optional[Path] = None,
        icons: Optional[Dict[str, str]] = None,
        priority_marks: Optional[Dict[str, str]] = None,
        max_queue: int = 50,
    ):
        self._config = config or get_config()
        self._dir = notification_dir or (self._config.data_dir / "notifications")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._latest_file = self._dir / "latest.json"
        self._queue_file = self._dir / "queue.json"
        self.icons = icons or NOTIFICATION_ICONS
        self.priority_marks = priority_marks or PRIORITY_MARKS
        self.max_queue = max_queue

    def push(
        self,
        ntype: str,
        message: str,
        priority: str = "normal",
        data: Optional[dict] = None,
    ) -> dict:
        """Add a notification to the queue.

        Args:
            ntype: Notification type (e.g., "message", "alert", "system").
            message: Human-readable message.
            priority: One of "urgent", "high", "normal", "low".
            data: Optional extra data dict.

        Returns:
            The notification dict that was created.
        """
        notification = {
            "timestamp": datetime.now().isoformat(),
            "type": ntype,
            "message": message,
            "priority": priority,
            "data": data or {},
            "read": False,
        }

        # Atomic write of latest
        tmp_path = self._latest_file.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(notification, f, ensure_ascii=False, indent=2)
        tmp_path.rename(self._latest_file)

        # Append to queue
        queue = self._load_queue()
        queue.append(notification)
        if len(queue) > self.max_queue:
            queue = queue[-self.max_queue:]
        self._save_queue(queue)

        return notification

    def get_unread(self) -> List[dict]:
        """Get all unread notifications."""
        return [n for n in self._load_queue() if not n.get("read")]

    def get_latest(self) -> Optional[dict]:
        """Get the most recent notification."""
        if self._latest_file.exists():
            try:
                with open(self._latest_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return None
        return None

    def mark_all_read(self) -> None:
        """Mark all notifications as read."""
        queue = self._load_queue()
        for n in queue:
            n["read"] = True
        self._save_queue(queue)

    def format(self, notifications: Optional[List[dict]] = None) -> str:
        """Format notifications for display.

        Args:
            notifications: List to format. Defaults to unread notifications.
        """
        if notifications is None:
            notifications = self.get_unread()
        if not notifications:
            return "No notifications"

        lines = [f"Notifications ({len(notifications)}):"]
        for n in notifications:
            icon = self.icons.get(n["type"], "\U0001f4cc")  # pushpin
            pmark = self.priority_marks.get(n["priority"], "")
            ts = n["timestamp"][11:16]  # HH:MM
            lines.append(f"  {pmark}{icon} [{ts}] {n['message']}")
        return "\n".join(lines)

    def _load_queue(self) -> list:
        if self._queue_file.exists():
            try:
                with open(self._queue_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []

    def _save_queue(self, queue: list) -> None:
        tmp_path = self._queue_file.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
        tmp_path.rename(self._queue_file)
