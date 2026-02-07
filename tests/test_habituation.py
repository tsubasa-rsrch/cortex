"""Tests for the habituation filter."""

import time
from cortex import HabituationFilter


def test_alert_above_threshold():
    h = HabituationFilter(base_threshold=10.0)
    ok, reason = h.should_notify("src", 15.0)
    assert ok
    assert "alert" in reason


def test_below_threshold():
    h = HabituationFilter(base_threshold=10.0)
    ok, reason = h.should_notify("src", 5.0)
    assert not ok
    assert "Below threshold" in reason


def test_orienting_response():
    h = HabituationFilter(base_threshold=10.0, orienting_mult=2.0)
    ok, reason = h.should_notify("src", 25.0)
    assert ok
    assert "Orienting" in reason


def test_cooldown():
    h = HabituationFilter(base_threshold=10.0, cooldown=60.0)
    ok1, _ = h.should_notify("src", 15.0)
    assert ok1
    ok2, reason = h.should_notify("src", 15.0)
    assert not ok2
    assert "Cooldown" in reason


def test_different_sources_independent():
    h = HabituationFilter(base_threshold=10.0, cooldown=60.0)
    ok1, _ = h.should_notify("src_a", 15.0)
    ok2, _ = h.should_notify("src_b", 15.0)
    assert ok1
    assert ok2


def test_habituation_raises_threshold():
    h = HabituationFilter(
        base_threshold=10.0,
        cooldown=0,
        window=300.0,
        habituate_count=3,
        habituated_mult=2.0,
    )
    # Trigger 3 times to habituate
    for _ in range(3):
        h.should_notify("src", 15.0)
    # Now threshold is 20.0, so 15.0 should NOT trigger
    ok, reason = h.should_notify("src", 15.0)
    assert not ok
    assert "Below threshold" in reason


def test_orienting_bypasses_cooldown():
    h = HabituationFilter(base_threshold=10.0, cooldown=60.0, orienting_mult=3.0)
    h.should_notify("src", 15.0)  # triggers, starts cooldown
    ok, reason = h.should_notify("src", 35.0)  # orienting
    assert ok
    assert "Orienting" in reason
