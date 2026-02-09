"""Tests for the Cosmos Reason2 bridge."""

import tempfile
import os
from cortex.bridges.cosmos import CortexCosmosBridge, CosmosConfig, EgocentricResult
from cortex.sources.base import Event


def _make_event(source="camera", etype="motion", content="test", priority=8, diff=25.0):
    return Event(
        source=source, type=etype, content=content,
        priority=priority, raw_data={"diff": diff}
    )


def test_bridge_creation():
    bridge = CortexCosmosBridge()
    stats = bridge.get_stats()
    assert stats["mock_mode"] is True
    assert stats["api_calls"] == 0
    assert stats["events_perceived"] == 0
    assert stats["model"] == "cosmos-reason2-8b"
    assert stats["circadian_mode"] is not None


def test_bridge_with_config():
    config = CosmosConfig(
        model_path="/tmp/test.gguf",
        server_port=9999,
        mock_mode=True,
    )
    bridge = CortexCosmosBridge(config=config)
    assert bridge.config.server_port == 9999
    assert bridge.server_url == "http://127.0.0.1:9999"


def test_perceive_filters_low_priority():
    bridge = CortexCosmosBridge()
    events = [_make_event(diff=3.0, priority=2)]
    passed = bridge.perceive(events)
    assert len(passed) == 0
    assert bridge._events_filtered == 1


def test_perceive_passes_high_priority():
    bridge = CortexCosmosBridge()
    events = [_make_event(diff=25.0, priority=8)]
    passed = bridge.perceive(events)
    assert len(passed) == 1
    assert passed[0].source == "camera"


def test_reason_about_scene_mock():
    bridge = CortexCosmosBridge()
    result = bridge.reason_about_scene("Is anyone looking at me?")
    assert isinstance(result, EgocentricResult)
    assert result.action == "engage"
    assert result.confidence > 0.5
    assert result.model == "cosmos-reason2-8b"


def test_reason_about_scene_motion():
    bridge = CortexCosmosBridge()
    result = bridge.reason_about_scene("I detect motion approaching me")
    assert result.action == "prepare_greeting"


def test_reason_about_scene_with_image():
    bridge = CortexCosmosBridge()
    # Create a tiny test image
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # minimal JPEG-ish
        tmp_path = f.name

    try:
        result = bridge.reason_about_scene("What do I see?", image_path=tmp_path)
        assert result.has_image is True
        assert result.scene_description != ""
    finally:
        os.unlink(tmp_path)


def test_perceive_and_reason_mock():
    bridge = CortexCosmosBridge()
    events = [_make_event(diff=30.0, priority=9, content="Large motion detected")]
    result = bridge.perceive_and_reason(events)
    assert result is not None
    assert result.events_analyzed >= 1


def test_perceive_and_reason_no_events():
    bridge = CortexCosmosBridge()
    events = [_make_event(diff=2.0, priority=1)]
    result = bridge.perceive_and_reason(events)
    assert result is None


def test_egocentric_event_summary():
    bridge = CortexCosmosBridge()
    events = [
        _make_event(source="camera", etype="motion", content="person walking"),
        _make_event(source="microphone", etype="audio", content="voice detected"),
    ]
    summary = bridge._summarize_events(events)
    assert "I detected movement" in summary
    assert "I heard something" in summary


def test_stats_tracking():
    bridge = CortexCosmosBridge()
    bridge.perceive([_make_event(diff=25.0)])
    bridge.perceive([_make_event(diff=2.0, priority=1)])
    bridge.reason_about_scene("test")

    stats = bridge.get_stats()
    assert stats["events_perceived"] == 1
    assert stats["events_filtered"] == 1
    assert stats["api_calls"] == 1
    assert "%" in stats["filter_rate"]


def test_mock_server_start():
    bridge = CortexCosmosBridge()  # mock_mode=True by default
    assert bridge.start_server() is True


def test_encode_image_nonexistent():
    bridge = CortexCosmosBridge()
    result = bridge._encode_image("/nonexistent/path.jpg")
    assert result is None
