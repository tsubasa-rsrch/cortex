"""Tests for the Gemini 3 bridge."""

from cortex.bridges.gemini import CortexGeminiBridge, GeminiConfig, ReasoningResult
from cortex.sources.base import Event


def _make_event(source="camera", etype="motion", content="test", priority=8, diff=25.0):
    return Event(
        source=source, type=etype, content=content,
        priority=priority, raw_data={"diff": diff}
    )


def test_bridge_creation():
    bridge = CortexGeminiBridge()
    stats = bridge.get_stats()
    assert stats["mock_mode"] is True
    assert stats["api_calls"] == 0
    assert stats["events_perceived"] == 0
    assert stats["circadian_mode"] is not None


def test_bridge_with_config():
    config = GeminiConfig(api_key="test-key", model="gemini-3-pro", mock_mode=True)
    bridge = CortexGeminiBridge(gemini_config=config)
    assert bridge.gemini_config.model == "gemini-3-pro"
    assert bridge.gemini_config.mock_mode is True


def test_perceive_filters_low_priority():
    bridge = CortexGeminiBridge()
    events = [_make_event(diff=3.0, priority=2)]
    passed = bridge.perceive(events)
    assert len(passed) == 0
    assert bridge._events_filtered == 1


def test_perceive_passes_high_priority():
    bridge = CortexGeminiBridge()
    events = [_make_event(diff=25.0, priority=8)]
    passed = bridge.perceive(events)
    assert len(passed) == 1
    assert passed[0].source == "camera"


def test_perceive_filters_repeated_stimuli():
    bridge = CortexGeminiBridge()
    events = [
        _make_event(source="cam1", diff=25.0),
        _make_event(source="cam1", diff=12.0),  # Same source, cooldown
    ]
    passed = bridge.perceive(events)
    assert len(passed) == 1  # Second event filtered by habituation


def test_perceive_passes_different_sources():
    bridge = CortexGeminiBridge()
    events = [
        _make_event(source="cam1", diff=25.0),
        _make_event(source="mic1", diff=18.0, etype="audio"),
    ]
    passed = bridge.perceive(events)
    assert len(passed) == 2  # Different sources both pass


def test_reason_mock_mode():
    bridge = CortexGeminiBridge()
    result = bridge.reason("What should I do about motion detected?")
    assert isinstance(result, ReasoningResult)
    assert result.reasoning != ""
    assert result.action != ""
    assert 0.0 <= result.confidence <= 1.0
    assert result.model == "gemini-3-flash-preview"
    assert bridge._api_calls == 1


def test_reason_urgent_night():
    bridge = CortexGeminiBridge()
    result = bridge.reason(
        "Analyze: priority: 8 motion at back door during night hours. Late Night mode."
    )
    assert result.confidence > 0.8
    assert "alert" in result.action or "investigate" in result.action


def test_reason_multimodal():
    bridge = CortexGeminiBridge()
    result = bridge.reason("motion detected and audio speech detected")
    assert result.confidence >= 0.7
    assert "monitor" in result.action


def test_perceive_and_reason_full_pipeline():
    bridge = CortexGeminiBridge()
    events = [
        _make_event(source="camera", etype="motion", content="Person at door", priority=8, diff=30.0),
        _make_event(source="mic", etype="audio", content="Doorbell", priority=6, diff=20.0),
    ]
    result = bridge.perceive_and_reason(events)
    assert result is not None
    assert isinstance(result, ReasoningResult)
    assert result.events_analyzed >= 2
    assert bridge._api_calls == 1


def test_perceive_and_reason_empty_after_filter():
    bridge = CortexGeminiBridge()
    events = [_make_event(diff=3.0, priority=1)]  # Low priority, filtered
    result = bridge.perceive_and_reason(events)
    assert result is None
    assert bridge._api_calls == 0  # No API call needed!


def test_reason_about_context():
    bridge = CortexGeminiBridge()
    # First perceive some events
    bridge.perceive([_make_event(content="Motion in zone A", diff=25.0)])
    # Then ask about context
    result = bridge.reason_about_context("What's happening right now?")
    assert result is not None
    assert result.reasoning != ""


def test_get_stats_after_operations():
    bridge = CortexGeminiBridge()
    events = [
        _make_event(source="cam1", diff=25.0),
        _make_event(source="cam1", diff=5.0, priority=2),  # Filtered
        _make_event(source="cam2", diff=20.0),
    ]
    bridge.perceive(events)
    bridge.reason("test query")

    stats = bridge.get_stats()
    assert stats["events_perceived"] == 2
    assert stats["events_filtered"] == 1
    assert stats["api_calls"] == 1
    assert "%" in stats["filter_rate"]


def test_notification_after_reasoning():
    bridge = CortexGeminiBridge()
    events = [_make_event(priority=9, diff=40.0)]
    bridge.perceive_and_reason(events)

    unread = bridge.notifications.get_unread()
    assert len(unread) >= 1
    # Should have a gemini_reasoning notification
    gemini_notifs = [n for n in unread if n.get("type") == "gemini_reasoning"]
    assert len(gemini_notifs) >= 1


def test_perception_context_building():
    bridge = CortexGeminiBridge()
    bridge.perceive([_make_event(content="Test event", diff=25.0)])
    context = bridge._build_perception_context()

    assert "time_mode" in context
    assert "energy_level" in context
    assert "recent_events" in context
    assert len(context["recent_events"]) == 1
    assert context["recent_events"][0]["content"] == "Test event"


def test_mock_response_varies_by_context():
    bridge = CortexGeminiBridge()

    # Normal event
    r1 = bridge._mock_gemini_response("motion detected at camera")
    # Urgent night event
    r2 = bridge._mock_gemini_response("priority: 9 motion at night Late Night")

    # Night urgent should have higher confidence
    assert r2["confidence"] > r1["confidence"]


def test_filter_rate_calculation():
    bridge = CortexGeminiBridge()
    # 3 events: 2 pass, 1 filtered
    bridge.perceive([
        _make_event(source="a", diff=25.0),
        _make_event(source="b", diff=20.0),
    ])
    bridge.perceive([
        _make_event(source="a", diff=5.0, priority=1),  # Filtered (low diff)
    ])

    stats = bridge.get_stats()
    # 1 filtered out of 3 total = 33.3%
    assert "33" in stats["filter_rate"]
