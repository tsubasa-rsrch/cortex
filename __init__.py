"""Cortex: Cognitive-science-based perception framework for AI agents.

Provides habituation, circadian rhythm, scheduling, decision-making,
notifications, and time tracking — all with zero external dependencies.

Quick start:
    from cortex import CortexConfig, set_config
    from cortex import HabituationFilter, CircadianRhythm, DecisionEngine

    # Optional: configure paths
    set_config(CortexConfig(data_dir="/tmp/my_agent", name="my-agent"))

    # Use modules
    hab = HabituationFilter()
    should_alert, reason = hab.should_notify("camera_1", 25.0)

    circadian = CircadianRhythm()
    status = circadian.check_and_update()
"""

from .config import CortexConfig, get_config, set_config
from .sources.base import Event, BaseSource
from .habituation import HabituationFilter
from .circadian import CircadianRhythm, CircadianMode
from .scheduler import Scheduler, ScheduledTask
from .notifications import NotificationQueue
from .timestamp_log import TimestampLog
from .decision import DecisionEngine, Action
from .defaults import (
    CIRCADIAN_SUGGESTIONS,
    CIRCADIAN_ACTIVITIES,
    AUTONOMOUS_ACTIVITIES,
    NOTIFICATION_ICONS,
    PRIORITY_MARKS,
)

__version__ = "0.1.0"

__all__ = [
    # Config
    "CortexConfig",
    "get_config",
    "set_config",
    # Sources
    "Event",
    "BaseSource",
    # Modules
    "HabituationFilter",
    "CircadianRhythm",
    "CircadianMode",
    "Scheduler",
    "ScheduledTask",
    "NotificationQueue",
    "TimestampLog",
    "DecisionEngine",
    "Action",
    # Defaults
    "CIRCADIAN_SUGGESTIONS",
    "CIRCADIAN_ACTIVITIES",
    "AUTONOMOUS_ACTIVITIES",
    "NOTIFICATION_ICONS",
    "PRIORITY_MARKS",
]
