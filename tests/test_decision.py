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
