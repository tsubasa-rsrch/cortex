#!/usr/bin/env python3
"""Cortex MCP Server — perception layer for any Claude Code session.

Exposes all Cortex cognitive modules as MCP tools, giving AI agents
real-time perception capabilities: habituation filtering, circadian
awareness, notification management, decision-making, and task tracking.

Usage:
    # Run directly
    python -m cortex.mcp_server

    # Add to Claude Code
    claude mcp add cortex-perception -- python -m cortex.mcp_server

    # Or in .mcp.json / ~/.claude.json:
    {
        "mcpServers": {
            "cortex-perception": {
                "command": "python3",
                "args": ["-m", "cortex.mcp_server"]
            }
        }
    }
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

from mcp.server.fastmcp import FastMCP

from cortex import (
    CortexConfig,
    set_config,
    HabituationFilter,
    CircadianRhythm,
    DecisionEngine,
    Action,
    Event,
    NotificationQueue,
    TimestampLog,
    Scheduler,
)

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Cortex Perception",
    instructions=(
        "Cortex provides cognitive-science-based perception tools for AI agents. "
        "Use these tools to filter noise (habituation), adapt to time of day "
        "(circadian), manage notifications, make decisions about events, "
        "track task timing, and schedule periodic work. "
        "Start with cortex_perception_summary for a full status overview."
    ),
)

# Global state — initialized lazily on first tool call
_state: dict[str, Any] = {}


def _get_state() -> dict[str, Any]:
    """Lazy-init all Cortex modules with shared config."""
    if not _state:
        config = CortexConfig(data_dir="/tmp/cortex_mcp", name="mcp-agent")
        set_config(config)

        hab = HabituationFilter(base_threshold=15.0)
        circadian = CircadianRhythm()
        circadian.check_and_update()  # initialize mode

        _state.update(
            config=config,
            habituation=hab,
            circadian=circadian,
            decision=DecisionEngine(),
            notifications=NotificationQueue(),
            timestamp_log=TimestampLog(),
            scheduler=Scheduler(),
        )
    return _state


# ---------------------------------------------------------------------------
# Tools: Habituation
# ---------------------------------------------------------------------------


@mcp.tool()
def cortex_check_habituation(source: str, value: float) -> dict:
    """Check if a stimulus from a source should trigger an alert.

    Uses cognitive habituation (sensory-specific adaptation) to filter
    repeated/low-value stimuli and only alert on novel or significant events.

    Args:
        source: Identifier for the stimulus source (e.g. "camera_1", "api_health")
        value: Numeric intensity of the stimulus (e.g. motion diff, error count)

    Returns:
        Dict with 'should_alert' (bool), 'reason' (str), and 'source' (str)
    """
    s = _get_state()
    should_alert, reason = s["habituation"].should_notify(source, value)
    return {
        "should_alert": should_alert,
        "reason": reason,
        "source": source,
        "value": value,
    }


# ---------------------------------------------------------------------------
# Tools: Circadian Rhythm
# ---------------------------------------------------------------------------


@mcp.tool()
def cortex_circadian_status() -> dict:
    """Get the current circadian (time-of-day) status and recommendations.

    Returns the current mode (morning/afternoon/evening/night), energy level,
    and suggested activities appropriate for the time of day. Inspired by
    the human suprachiasmatic nucleus and cortisol/melatonin cycles.

    Returns:
        Dict with 'mode', 'changed', 'energy', 'suggestions', and 'hour'
    """
    s = _get_state()
    result = s["circadian"].check_and_update()
    suggestions = s["circadian"].get_current_suggestions()

    # Extract suggestion text safely
    suggestion_texts = []
    for sg in suggestions[:5]:
        if isinstance(sg, dict):
            suggestion_texts.append(sg.get("message", sg.get("text", str(sg))))
        else:
            suggestion_texts.append(str(sg))

    return {
        "mode": result["mode"].value,
        "changed": result["changed"],
        "energy": result.get("energy", "unknown"),
        "suggestions": suggestion_texts,
        "hour": time.localtime().tm_hour,
    }


# ---------------------------------------------------------------------------
# Tools: Notifications
# ---------------------------------------------------------------------------


@mcp.tool()
def cortex_push_notification(
    ntype: str, message: str, priority: str = "normal"
) -> dict:
    """Push a notification to the Cortex notification queue.

    Implements the cognitive orienting response — routing alerts by urgency
    level so the agent can triage what needs immediate attention.

    Args:
        ntype: Notification type (e.g. "alert", "message", "task", "error")
        message: Human-readable notification text
        priority: Priority level — "normal" or "urgent"

    Returns:
        Dict with 'success' and 'queue_size'
    """
    s = _get_state()
    s["notifications"].push(ntype, message, priority=priority)
    unread = s["notifications"].get_unread()
    return {"success": True, "queue_size": len(unread)}


@mcp.tool()
def cortex_get_notifications(mark_read: bool = False) -> dict:
    """Get unread notifications from the Cortex queue.

    Args:
        mark_read: If True, mark all notifications as read after retrieval

    Returns:
        Dict with 'count', 'notifications' list, and 'formatted' text
    """
    s = _get_state()
    unread = s["notifications"].get_unread()
    formatted = s["notifications"].format()

    result = {
        "count": len(unread),
        "notifications": unread,
        "formatted": formatted,
    }

    if mark_read:
        s["notifications"].mark_all_read()

    return result


# ---------------------------------------------------------------------------
# Tools: Decision Engine
# ---------------------------------------------------------------------------


@mcp.tool()
def cortex_decide(events_json: str = "[]") -> dict:
    """Decide what action to take based on incoming events.

    Uses a salience-network-inspired decision engine to prioritize events
    and route them to appropriate actions. When no events are pending,
    suggests an autonomous activity using weighted random selection.

    Args:
        events_json: JSON array of event objects. Each event should have:
            - source (str): Event origin (e.g. "camera", "api", "user")
            - type (str): Event type (e.g. "motion", "message", "error")
            - content (str): Description of the event
            - priority (int): 1-10, higher = more important

    Returns:
        Dict with 'action_name', 'description', 'triggered_by', and 'priority'
    """
    s = _get_state()

    try:
        raw_events = json.loads(events_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON for events_json"}

    events = []
    for e in raw_events:
        events.append(
            Event(
                source=e.get("source", "unknown"),
                type=e.get("type", "generic"),
                content=e.get("content", ""),
                priority=e.get("priority", 5),
                raw_data=e.get("raw_data", {}),
            )
        )

    action = s["decision"].decide(events)
    return {
        "action_name": action.name,
        "description": action.description,
        "triggered_by": events[0].content if events else "idle",
        "priority": events[0].priority if events else 0,
    }


# ---------------------------------------------------------------------------
# Tools: Timestamp Log (task tracking)
# ---------------------------------------------------------------------------


@mcp.tool()
def cortex_start_task(task_name: str) -> dict:
    """Start tracking a new task with timestamps.

    Based on episodic memory encoding — preserves temporal context
    so the agent can recall when things happened and how long they took.

    Args:
        task_name: Human-readable name for the task

    Returns:
        Dict with 'task', 'started_at', and 'status'
    """
    s = _get_state()
    s["timestamp_log"].start_task(task_name)
    status = s["timestamp_log"].get_status()
    return {
        "task": task_name,
        "started_at": status.get("current_task_start", "now"),
        "status": "in_progress",
    }


@mcp.tool()
def cortex_checkpoint(note: str) -> dict:
    """Add a checkpoint to the current task.

    Args:
        note: Description of what was accomplished at this checkpoint

    Returns:
        Dict with 'checkpoint', 'elapsed_since_start'
    """
    s = _get_state()
    result = s["timestamp_log"].checkpoint(note)
    if result is None:
        return {"error": "No active task to checkpoint"}
    return {
        "checkpoint": note,
        "elapsed_minutes": result.get("elapsed_min", 0),
        "task": result.get("task", "unknown"),
    }


@mcp.tool()
def cortex_end_task(summary: str = "") -> dict:
    """End the current task and get timing summary.

    Args:
        summary: Optional summary of the completed task

    Returns:
        Dict with task timing details
    """
    s = _get_state()
    result = s["timestamp_log"].end_task(summary or "completed")
    return {
        "task": result.get("task", "unknown"),
        "elapsed_minutes": round(result.get("elapsed_min", 0), 2),
        "checkpoints": result.get("checkpoints", []),
        "summary": summary,
        "status": "completed",
    }


# ---------------------------------------------------------------------------
# Tools: Scheduler
# ---------------------------------------------------------------------------


@mcp.tool()
def cortex_schedule(name: str, interval_seconds: int, description: str = "") -> dict:
    """Register a periodic task with the Cortex scheduler.

    Based on ultradian rhythms — manages recurring tasks that need to
    run at regular intervals (health checks, syncs, cleanups, etc.).

    Args:
        name: Unique task identifier
        interval_seconds: How often the task should run (in seconds)
        description: Optional human-readable description

    Returns:
        Dict with 'registered', 'name', and 'interval'
    """
    s = _get_state()
    # MCP tools can't pass callbacks, so we register a no-op.
    # The caller should check cortex_check_schedule() and act on due tasks.
    s["scheduler"].register(
        name,
        interval_seconds=interval_seconds,
        callback=lambda: {"task": name, "status": "triggered"},
    )
    return {
        "registered": True,
        "name": name,
        "interval_seconds": interval_seconds,
        "description": description,
    }


@mcp.tool()
def cortex_check_schedule() -> dict:
    """Check which scheduled tasks are due and run them.

    Returns:
        Dict with 'due_tasks' and 'all_tasks' status
    """
    s = _get_state()
    results = s["scheduler"].check_and_run()
    status = s["scheduler"].get_status()
    return {
        "ran_tasks": list(results.keys()),
        "all_tasks": status,
    }


# ---------------------------------------------------------------------------
# Tools: Perception Summary (all-in-one)
# ---------------------------------------------------------------------------


@mcp.tool()
def cortex_perception_summary() -> dict:
    """Get a comprehensive perception summary from all Cortex modules.

    This is the primary tool for getting a holistic view of the agent's
    perceptual state: circadian mode, pending notifications, active tasks,
    and scheduled work. Call this at the start of a session or when you
    need a full status overview.

    Returns:
        Dict with circadian, notifications, task, and scheduler status
    """
    s = _get_state()

    # Circadian
    circadian_result = s["circadian"].check_and_update()
    suggestions = s["circadian"].get_current_suggestions()
    suggestion_texts = []
    for sg in suggestions[:3]:
        if isinstance(sg, dict):
            suggestion_texts.append(sg.get("message", sg.get("text", str(sg))))
        else:
            suggestion_texts.append(str(sg))

    # Notifications
    unread = s["notifications"].get_unread()

    # Task
    task_status = s["timestamp_log"].get_status()
    current_task = task_status.get("current_task")
    if current_task and isinstance(current_task, dict):
        task_info = {
            "active": True,
            "name": current_task.get("name", "unknown"),
            "elapsed_min": round(current_task.get("elapsed_min", 0), 2),
        }
    else:
        task_info = {"active": False, "name": "none", "elapsed_min": 0}

    # Scheduler
    sched_status = s["scheduler"].get_status()

    return {
        "circadian": {
            "mode": circadian_result["mode"].value,
            "energy": circadian_result.get("energy", "unknown"),
            "suggestions": suggestion_texts,
        },
        "notifications": {
            "unread_count": len(unread),
            "formatted": s["notifications"].format() if unread else "No unread notifications.",
        },
        "current_task": task_info,
        "scheduler": {
            "registered_tasks": len(sched_status) if isinstance(sched_status, list) else 0,
            "details": sched_status,
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Run the Cortex MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
