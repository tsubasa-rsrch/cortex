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


def test_habituated_still_triggers_above_raised_threshold():
    """After habituation, values above raised threshold still trigger."""
    h = HabituationFilter(
        base_threshold=10.0, cooldown=0, window=300.0,
        habituate_count=3, habituated_mult=1.5, orienting_mult=3.0,
    )
    for _ in range(3):
        h.should_notify("src", 15.0)
    # Threshold is now 15.0 (habituated), orienting at 30.0
    # Value 20.0 is above habituated threshold but below orienting
    ok, reason = h.should_notify("src", 20.0)
    assert ok
    assert "habituated" in reason


def test_exact_threshold_value():
    """Value exactly at threshold triggers notification."""
    h = HabituationFilter(base_threshold=10.0, cooldown=0)
    ok, reason = h.should_notify("src", 10.0)
    assert ok


def test_exact_orienting_threshold():
    """Value exactly at orienting threshold triggers."""
    h = HabituationFilter(base_threshold=10.0, orienting_mult=2.0, cooldown=0)
    ok, reason = h.should_notify("src", 20.0)
    assert ok
    assert "Orienting" in reason


def test_history_is_recorded():
    """Each call records to history."""
    h = HabituationFilter(base_threshold=10.0, cooldown=0)
    h.should_notify("src", 5.0)
    h.should_notify("src", 5.0)
    assert len(h.history["src"]) == 2


def test_multiple_sources_isolate_habituation():
    """Habituation on source A doesn't affect source B."""
    h = HabituationFilter(
        base_threshold=10.0, cooldown=0, habituate_count=3, habituated_mult=2.0,
    )
    for _ in range(3):
        h.should_notify("A", 15.0)
    # Source A is habituated, source B is not
    ok_a, _ = h.should_notify("A", 15.0)
    ok_b, _ = h.should_notify("B", 15.0)
    assert not ok_a  # habituated, 15 < 20
    assert ok_b  # fresh, 15 >= 10
