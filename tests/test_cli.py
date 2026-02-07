"""Tests for cortex.cli module."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


def test_cli_module_import():
    """CLI module should be importable."""
    from cortex.cli import replay_main
    assert callable(replay_main)


def test_replay_with_sample_file():
    """Replay should work with a sample events file."""
    # Create temp events file
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
    events = []
    for i in range(20):
        diff = 10.0 + i * 2
        events.append({
            "timestamp": f"2026-02-07T{10+i//6:02d}:{(i*10)%60:02d}:00",
            "type": "motion",
            "content": f"test: diff={diff:.1f}",
            "metadata": {"camera": "test_cam", "diff": diff, "urgency": "normal"},
        })
    for e in events:
        tmp.write(json.dumps(e) + "\n")
    tmp.close()

    # Test with --log argument
    with patch.object(sys, "argv", ["cortex-replay", "--log", tmp.name]):
        from cortex.cli import replay_main
        # Should not raise
        replay_main()

    Path(tmp.name).unlink()


def test_replay_no_log_uses_synthetic():
    """Replay should fall back to synthetic data when log is missing."""
    with patch.object(sys, "argv", ["cortex-replay", "--log", "/tmp/nonexistent_events.jsonl"]):
        from cortex.cli import replay_main
        # Should not raise — falls back to synthetic data
        replay_main()


def test_replay_verbose_flag():
    """Verbose flag should be accepted."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
    events = [
        {
            "timestamp": "2026-02-07T12:00:00",
            "type": "motion",
            "content": "test: diff=25.0",
            "metadata": {"camera": "cam1", "diff": 25.0},
        }
    ]
    for e in events:
        tmp.write(json.dumps(e) + "\n")
    tmp.close()

    with patch.object(sys, "argv", ["cortex-replay", "--log", tmp.name, "--verbose"]):
        from cortex.cli import replay_main
        replay_main()

    Path(tmp.name).unlink()
