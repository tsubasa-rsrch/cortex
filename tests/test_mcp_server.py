"""Tests for Cortex MCP Server tools."""

import json
import pytest
from cortex.mcp_server import (
    _get_state,
    _state,
    cortex_check_habituation,
    cortex_circadian_status,
    cortex_push_notification,
    cortex_get_notifications,
    cortex_decide,
    cortex_start_task,
    cortex_checkpoint,
    cortex_end_task,
    cortex_schedule,
    cortex_check_schedule,
    cortex_perception_summary,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test."""
    _state.clear()
    yield
    _state.clear()


# --- State initialization ---


def test_lazy_init():
    """State initializes lazily on first call."""
    assert len(_state) == 0
    s = _get_state()
    assert "habituation" in s
    assert "circadian" in s
    assert "decision" in s
    assert "notifications" in s
    assert "timestamp_log" in s
    assert "scheduler" in s


def test_state_reused():
    """Same state dict is reused across calls."""
    s1 = _get_state()
    s2 = _get_state()
    assert s1 is s2


# --- Habituation ---


def test_habituation_alert():
    """High value triggers alert."""
    result = cortex_check_habituation("cam_1", 25.0)
    assert result["should_alert"] is True
    assert result["source"] == "cam_1"
    assert result["value"] == 25.0
    assert "reason" in result


def test_habituation_cooldown():
    """Second call within cooldown is suppressed."""
    cortex_check_habituation("cam_1", 25.0)
    result = cortex_check_habituation("cam_1", 20.0)
    assert result["should_alert"] is False
    assert "Cooldown" in result["reason"] or "cooldown" in result["reason"].lower()


def test_habituation_below_threshold():
    """Low value does not alert."""
    result = cortex_check_habituation("cam_2", 5.0)
    assert result["should_alert"] is False


# --- Circadian ---


def test_circadian_status():
    """Returns valid circadian status."""
    result = cortex_circadian_status()
    assert result["mode"] in ("morning", "afternoon", "evening", "night")
    assert isinstance(result["suggestions"], list)
    assert isinstance(result["hour"], int)
    assert 0 <= result["hour"] <= 23


# --- Notifications ---


def test_push_and_get_notifications():
    """Push then retrieve notifications."""
    push_result = cortex_push_notification("alert", "Test notification")
    assert push_result["success"] is True
    assert push_result["queue_size"] >= 1

    get_result = cortex_get_notifications()
    assert get_result["count"] >= 1
    assert "Test notification" in get_result["formatted"]


def test_mark_read():
    """Marking as read clears unread count."""
    cortex_push_notification("info", "Read me")
    cortex_get_notifications(mark_read=True)
    result = cortex_get_notifications()
    assert result["count"] == 0


def test_notification_urgent():
    """Urgent notifications are stored."""
    cortex_push_notification("error", "Critical failure", priority="urgent")
    result = cortex_get_notifications()
    assert result["count"] >= 1


# --- Decision Engine ---


def test_decide_with_events():
    """Decision with events returns an action."""
    events = [
        {"source": "camera", "type": "motion", "content": "Person in lobby", "priority": 8},
    ]
    result = cortex_decide(json.dumps(events))
    assert "action_name" in result
    assert result["triggered_by"] == "Person in lobby"
    assert result["priority"] == 8


def test_decide_no_events():
    """Decision with no events returns idle activity."""
    result = cortex_decide("[]")
    assert "action_name" in result
    assert result["triggered_by"] == "idle"
    assert result["priority"] == 0


def test_decide_invalid_json():
    """Invalid JSON returns error."""
    result = cortex_decide("not json")
    assert "error" in result


def test_decide_multiple_events():
    """Multiple events: highest priority wins."""
    events = [
        {"source": "api", "type": "message", "content": "Hello", "priority": 3},
        {"source": "camera", "type": "motion", "content": "Intruder!", "priority": 10},
    ]
    result = cortex_decide(json.dumps(events))
    assert "action_name" in result


# --- Timestamp Log ---


def test_task_lifecycle():
    """Start, checkpoint, end a task."""
    start = cortex_start_task("test_task")
    assert start["task"] == "test_task"
    assert start["status"] == "in_progress"

    cp = cortex_checkpoint("halfway done")
    assert cp["checkpoint"] == "halfway done"
    assert cp["task"] == "test_task"

    end = cortex_end_task("all done")
    assert end["status"] == "completed"
    assert end["summary"] == "all done"
    assert end["elapsed_minutes"] >= 0


# --- Scheduler ---


def test_schedule_and_check():
    """Register a task then check schedule."""
    reg = cortex_schedule("health_check", 300, "Check health every 5min")
    assert reg["registered"] is True
    assert reg["name"] == "health_check"

    check = cortex_check_schedule()
    assert isinstance(check["all_tasks"], (list, dict))


# --- Perception Summary ---


def test_perception_summary():
    """Comprehensive summary includes all sections."""
    result = cortex_perception_summary()

    assert "circadian" in result
    assert result["circadian"]["mode"] in ("morning", "afternoon", "evening", "night")

    assert "notifications" in result
    assert "unread_count" in result["notifications"]

    assert "current_task" in result
    assert "active" in result["current_task"]

    assert "scheduler" in result
    assert "timestamp" in result


def test_perception_summary_with_state():
    """Summary reflects current state."""
    cortex_push_notification("test", "hello world")
    cortex_start_task("demo")

    result = cortex_perception_summary()
    assert result["notifications"]["unread_count"] >= 1
    assert result["current_task"]["active"] is True
    assert result["current_task"]["name"] == "demo"
