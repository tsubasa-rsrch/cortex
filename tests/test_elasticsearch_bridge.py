"""Tests for the Elasticsearch bridge."""

from cortex.bridges.elasticsearch import CortexElasticBridge, ESConfig, IndexedEvent
from cortex.sources.base import Event


def _make_event(source="camera", etype="motion", content="test", priority=8, diff=25.0):
    return Event(
        source=source, type=etype, content=content,
        priority=priority, raw_data={"diff": diff}
    )


def test_bridge_creation():
    bridge = CortexElasticBridge()
    stats = bridge.get_stats()
    assert stats["mock_mode"] is True
    assert stats["total_indexed"] == 0
    assert stats["circadian_mode"] is not None


def test_index_event_passes_high_diff():
    bridge = CortexElasticBridge()
    event = _make_event(diff=25.0)
    result = bridge.index_event(event)
    assert result is not None
    assert isinstance(result, IndexedEvent)
    assert result.doc_id == "mock-1"


def test_index_event_filters_low_diff():
    bridge = CortexElasticBridge()
    event = _make_event(diff=3.0, priority=2)
    result = bridge.index_event(event)
    assert result is None


def test_filter_event_returns_event_or_none():
    bridge = CortexElasticBridge()
    high = _make_event(diff=30.0)
    low = _make_event(diff=1.0, priority=1)
    assert bridge.filter_event(high) is not None
    assert bridge.filter_event(low) is None


def test_get_agent_context_empty():
    bridge = CortexElasticBridge()
    ctx = bridge.get_agent_context()
    assert "cortex_perception" in ctx
    assert ctx["cortex_perception"]["recent_events"] == []
    assert "No recent events" in ctx["cortex_perception"]["perception_summary"]


def test_get_agent_context_with_events():
    bridge = CortexElasticBridge()
    bridge.index_event(_make_event(diff=25.0))
    bridge.index_event(_make_event(source="audio", etype="sound", diff=20.0))
    ctx = bridge.get_agent_context()
    assert len(ctx["cortex_perception"]["recent_events"]) == 2
    assert "motion" in ctx["cortex_perception"]["perception_summary"]


def test_build_agent_system_prompt():
    bridge = CortexElasticBridge()
    prompt = bridge.build_agent_system_prompt("Base prompt here.")
    assert "Base prompt here." in prompt
    assert "## Cortex Perception Context" in prompt
    assert "Current mode:" in prompt


def test_index_name_format():
    bridge = CortexElasticBridge()
    name = bridge._get_index_name()
    assert name.startswith("cortex-events-")
    assert "." in name  # date has dots


def test_event_to_document():
    bridge = CortexElasticBridge()
    event = _make_event(content="Hello")
    doc = bridge._event_to_document(event)
    assert "@timestamp" in doc
    assert doc["source"] == "camera"
    assert doc["content"] == "Hello"
    assert "cortex" in doc
    assert doc["cortex"]["habituation_passed"] is True


def test_custom_es_config():
    config = ESConfig(
        es_url="https://test.es.io:443",
        api_key="test-key",
        index_prefix="my-events",
        mock_mode=True,
    )
    bridge = CortexElasticBridge(es_config=config)
    assert bridge.es_config.index_prefix == "my-events"
    name = bridge._get_index_name()
    assert name.startswith("my-events-")


def test_notifications_pushed_on_index():
    bridge = CortexElasticBridge()
    bridge.index_event(_make_event(diff=25.0))
    unread = bridge.notifications.get_unread()
    assert len(unread) >= 1


def test_stats_after_indexing():
    bridge = CortexElasticBridge()
    bridge.index_event(_make_event(diff=25.0))
    bridge.index_event(_make_event(diff=30.0))
    stats = bridge.get_stats()
    assert stats["total_indexed"] == 2
    assert stats["last_event"] is not None


def test_perception_summary_format():
    bridge = CortexElasticBridge()
    bridge.index_event(_make_event(etype="motion", diff=25.0))
    bridge.index_event(_make_event(etype="sound", diff=20.0, source="audio"))
    summary = bridge._build_summary(bridge._indexed_events)
    assert "motion" in summary
    assert "sound" in summary
    assert "mode" in summary


def test_multiple_sources_indexed():
    bridge = CortexElasticBridge()
    e1 = bridge.index_event(_make_event(source="cam1", diff=25.0))
    e2 = bridge.index_event(_make_event(source="cam2", diff=30.0))
    assert e1 is not None
    assert e2 is not None
    assert e1.doc_id != e2.doc_id
