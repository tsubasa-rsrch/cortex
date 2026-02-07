"""Tests for the decision engine."""

from cortex import DecisionEngine, Action, Event


def test_autonomous_activity():
    de = DecisionEngine()
    action = de.choose_autonomous_activity()
    assert isinstance(action, Action)
    assert action.name


def test_decide_with_no_events():
    de = DecisionEngine()
    action = de.decide([])
    assert isinstance(action, Action)


def test_decide_with_events():
    de = DecisionEngine()
    events = [
        Event(source="sensor", type="motion", content="Movement detected", priority=7),
        Event(source="api", type="message", content="Hello", priority=3),
    ]
    action = de.decide(events)
    assert "sensor" in action.description  # highest priority event


def test_custom_event_handler():
    def handle_sensor(event):
        return Action("custom_action", f"Custom: {event.content}")

    de = DecisionEngine(event_handlers={"sensor": handle_sensor})
    events = [Event(source="sensor", type="motion", content="beep", priority=5)]
    action = de.decide(events)
    assert action.name == "custom_action"


def test_custom_activities():
    activities = [
        {"name": "dance", "description": "Dance around", "weight": 10.0},
    ]
    de = DecisionEngine(activities=activities)
    action = de.choose_autonomous_activity()
    assert action.name == "dance"


def test_action_execute_no_handler():
    a = Action("test", "A test action")
    result = a.execute()
    assert result["status"] == "ok"


def test_action_execute_with_handler():
    a = Action("add", "Add numbers", params={"a": 1, "b": 2}, handler=lambda a, b: a + b)
    result = a.execute()
    assert result["status"] == "ok"
    assert result["result"] == 3


def test_action_execute_error():
    def fail():
        raise ValueError("boom")
    a = Action("fail", "Will fail", handler=fail)
    result = a.execute()
    assert result["status"] == "error"
    assert "boom" in result["error"]


def test_priority_ordering():
    """Higher priority events are processed first."""
    de = DecisionEngine()
    events = [
        Event(source="low", type="info", content="Low priority", priority=1),
        Event(source="high", type="alert", content="High priority", priority=10),
        Event(source="mid", type="info", content="Mid priority", priority=5),
    ]
    action = de.decide(events)
    assert "high" in action.description


def test_action_default_params():
    """Action params defaults to empty dict."""
    a = Action("test", "desc")
    assert a.params == {}


def test_single_event():
    """Single event is processed correctly."""
    de = DecisionEngine()
    events = [Event(source="cam", type="motion", content="Move!", priority=5)]
    action = de.decide(events)
    assert action.name == "process_event"
    assert "cam" in action.description


def test_handler_overrides_default():
    """Custom handler overrides default event processing."""
    calls = []
    def handler(event):
        calls.append(event)
        return Action("handled", "Was handled")

    de = DecisionEngine(event_handlers={"cam": handler})
    events = [Event(source="cam", type="motion", content="test", priority=5)]
    action = de.decide(events)
    assert action.name == "handled"
    assert len(calls) == 1
