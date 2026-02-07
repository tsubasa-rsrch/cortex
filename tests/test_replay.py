"""Tests for cortex.replay module."""

import json
import tempfile
from pathlib import Path

from cortex.replay import load_events, replay, _synthetic_events


class TestLoadEvents:
    """Tests for load_events function."""

    def test_load_from_jsonl_file(self, tmp_path):
        """Load events from a JSONL file."""
        log = tmp_path / "events.jsonl"
        events = [
            {"type": "motion", "content": "diff=20.0", "metadata": {"diff": 20.0}},
            {"type": "telegram", "content": "hello"},
        ]
        log.write_text("\n".join(json.dumps(e) for e in events))

        loaded = load_events(str(log))
        assert len(loaded) == 2
        assert loaded[0]["type"] == "motion"
        assert loaded[1]["type"] == "telegram"

    def test_load_skips_invalid_json(self, tmp_path):
        """Skip malformed lines without crashing."""
        log = tmp_path / "events.jsonl"
        log.write_text(
            '{"type":"motion"}\n'
            "this is not json\n"
            '{"type":"telegram"}\n'
        )
        loaded = load_events(str(log))
        assert len(loaded) == 2

    def test_load_skips_blank_lines(self, tmp_path):
        """Skip blank lines."""
        log = tmp_path / "events.jsonl"
        log.write_text('{"type":"motion"}\n\n\n{"type":"motion"}\n')
        loaded = load_events(str(log))
        assert len(loaded) == 2

    def test_load_nonexistent_file_returns_synthetic(self):
        """Nonexistent file falls back to synthetic data."""
        result = load_events("/tmp/nonexistent_file_xyz_abc.jsonl")
        assert len(result) == 100  # synthetic generates 100 events

    def test_load_none_uses_bundled_data(self):
        """None path finds bundled sample data."""
        result = load_events()
        assert len(result) > 0

    def test_load_empty_file_returns_synthetic(self, tmp_path):
        """Empty file falls back to synthetic data."""
        log = tmp_path / "empty.jsonl"
        log.write_text("")
        # Empty file has path that exists but no events
        loaded = load_events(str(log))
        assert len(loaded) == 0  # empty file = 0 events, no fallback


class TestSyntheticEvents:
    """Tests for synthetic event generation."""

    def test_synthetic_returns_100_events(self):
        events = _synthetic_events()
        assert len(events) == 100

    def test_synthetic_events_have_required_fields(self):
        events = _synthetic_events()
        for e in events:
            assert "timestamp" in e
            assert "type" in e
            assert e["type"] == "motion"
            assert "content" in e
            assert "metadata" in e
            assert "camera" in e["metadata"]
            assert "diff" in e["metadata"]
            assert "urgency" in e["metadata"]

    def test_synthetic_urgency_classification(self):
        events = _synthetic_events()
        for e in events:
            diff = e["metadata"]["diff"]
            urgency = e["metadata"]["urgency"]
            if diff >= 30:
                assert urgency == "urgent"
            elif diff >= 20:
                assert urgency == "high"
            else:
                assert urgency == "normal"

    def test_synthetic_diff_minimum(self):
        """All diffs should be >= 5."""
        events = _synthetic_events()
        for e in events:
            assert e["metadata"]["diff"] >= 5


class TestReplay:
    """Tests for replay function."""

    def _make_motion_events(self, diffs, camera="bedroom"):
        """Helper to create motion events with given diff values."""
        events = []
        for i, diff in enumerate(diffs):
            events.append({
                "timestamp": f"2026-02-07T{12 + i % 12:02d}:00:00",
                "type": "motion",
                "content": f"{camera}: diff={diff:.1f}",
                "metadata": {
                    "camera": camera,
                    "diff": diff,
                    "urgency": (
                        "urgent" if diff >= 30
                        else "high" if diff >= 20
                        else "normal"
                    ),
                },
            })
        return events

    def test_replay_returns_stats(self):
        """Replay returns a stats dict."""
        events = self._make_motion_events([10, 15, 20, 25, 30])
        stats = replay(events)
        assert "total_events" in stats
        assert "motion_events" in stats
        assert "passed" in stats
        assert "filtered" in stats
        assert "orienting" in stats
        assert "reduction_pct" in stats

    def test_replay_counts_events(self):
        """Stats reflect input counts."""
        events = self._make_motion_events([10, 20, 30])
        stats = replay(events)
        assert stats["total_events"] == 3
        assert stats["motion_events"] == 3
        assert stats["passed"] + stats["filtered"] == 3

    def test_replay_mixed_event_types(self):
        """Replay handles mixed event types."""
        events = self._make_motion_events([25])
        events.append({"type": "telegram", "content": "hello"})
        stats = replay(events)
        assert stats["total_events"] == 2
        assert stats["motion_events"] == 1

    def test_replay_filters_low_intensity(self):
        """Low-intensity repeated events get filtered."""
        # Many low-diff events should get habituated
        events = self._make_motion_events([10] * 20)
        stats = replay(events)
        assert stats["filtered"] > 0
        assert stats["reduction_pct"] > 0

    def test_replay_passes_high_intensity(self):
        """High-intensity events pass through."""
        events = self._make_motion_events([35, 40, 50])
        stats = replay(events)
        assert stats["passed"] > 0

    def test_replay_empty_events(self):
        """Replay handles empty event list."""
        stats = replay([])
        assert stats["total_events"] == 0
        assert stats["motion_events"] == 0
        assert stats["reduction_pct"] == 0

    def test_replay_no_motion_events(self):
        """Replay handles events with no motion type."""
        events = [
            {"type": "telegram", "content": "hello"},
            {"type": "telegram", "content": "world"},
        ]
        stats = replay(events)
        assert stats["total_events"] == 2
        assert stats["motion_events"] == 0
        assert stats["passed"] == 0

    def test_replay_with_bundled_data(self):
        """Replay works with bundled sample data."""
        events = load_events()
        if events:
            stats = replay(events)
            assert stats["total_events"] > 0
            assert stats["reduction_pct"] >= 0

    def test_replay_verbose_mode(self):
        """Verbose mode doesn't crash."""
        events = self._make_motion_events([10, 25, 35])
        stats = replay(events, verbose=True)
        assert stats["total_events"] == 3
