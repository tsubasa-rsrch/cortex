"""Tests for the task scheduler."""

from cortex import Scheduler, CortexConfig


def test_register_and_run(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    sched = Scheduler(config=cfg)
    results = []
    sched.register("t1", 0, lambda: results.append(1), description="test")
    sched.check_and_run()
    assert len(results) == 1


def test_interval_prevents_rerun(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    sched = Scheduler(config=cfg)
    count = []
    sched.register("t1", 9999, lambda: count.append(1))
    sched.check_and_run()
    sched.check_and_run()
    assert len(count) == 1  # only ran once


def test_unregister(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    sched = Scheduler(config=cfg)
    sched.register("t1", 0, lambda: None)
    assert sched.unregister("t1")
    assert not sched.unregister("nonexistent")


def test_enable_disable(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    sched = Scheduler(config=cfg)
    count = []
    sched.register("t1", 0, lambda: count.append(1), enabled=False)
    sched.check_and_run()
    assert len(count) == 0
    sched.enable("t1")
    sched.check_and_run()
    assert len(count) == 1


def test_get_status(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    sched = Scheduler(config=cfg)
    sched.register("t1", 300, lambda: None, description="five min task")
    status = sched.get_status()
    assert "t1" in status
    assert status["t1"]["interval_human"] == "5m"


def test_state_persistence(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    sched1 = Scheduler(config=cfg)
    count = []
    sched1.register("t1", 9999, lambda: count.append(1))
    sched1.check_and_run()

    # New scheduler should restore state
    sched2 = Scheduler(config=cfg)
    sched2.register("t1", 9999, lambda: count.append(1))
    sched2.check_and_run()
    assert len(count) == 1  # not re-run


def test_callback_exception_returns_error(tmp_path):
    """Task callback raising exception returns error dict."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    sched = Scheduler(config=cfg)
    sched.register("bad", 0, lambda: 1 / 0)
    results = sched.check_and_run()
    assert "bad" in results
    assert results["bad"]["success"] is False
    assert "error" in results["bad"]


def test_callback_return_value(tmp_path):
    """Task callback return value is captured in results."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    sched = Scheduler(config=cfg)
    sched.register("greet", 0, lambda: "hello")
    results = sched.check_and_run()
    assert results["greet"]["success"] is True
    assert results["greet"]["result"] == "hello"


def test_multiple_tasks(tmp_path):
    """Multiple tasks can run in single check."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    sched = Scheduler(config=cfg)
    a, b = [], []
    sched.register("a", 0, lambda: a.append(1))
    sched.register("b", 0, lambda: b.append(1))
    results = sched.check_and_run()
    assert "a" in results and "b" in results
    assert len(a) == 1 and len(b) == 1


def test_disable_nonexistent_returns_false(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    sched = Scheduler(config=cfg)
    assert sched.disable("nope") is False
    assert sched.enable("nope") is False


def test_time_until_next(tmp_path):
    """time_until_next returns 0 for never-run tasks."""
    from cortex.scheduler import ScheduledTask
    task = ScheduledTask("t", 60, lambda: None)
    assert task.time_until_next() == 0
    task.run()
    remaining = task.time_until_next()
    assert 0 < remaining <= 60


def test_format_interval():
    """_format_interval handles seconds, minutes, hours."""
    from cortex.scheduler import _format_interval
    assert _format_interval(30) == "30s"
    assert _format_interval(300) == "5m"
    assert _format_interval(3600) == "1h"
    assert _format_interval(3900) == "1h5m"
    assert _format_interval(7200) == "2h"


def test_status_interval_human(tmp_path):
    """Status shows human-readable interval."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    sched = Scheduler(config=cfg)
    sched.register("hourly", 3600, lambda: None, description="every hour")
    status = sched.get_status()
    assert status["hourly"]["interval_human"] == "1h"
    assert status["hourly"]["description"] == "every hour"


def test_corrupt_state_file(tmp_path):
    """Corrupt state file doesn't crash."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    state_file = cfg.state_file("scheduler_state.json")
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("{broken json!!!")
    sched = Scheduler(config=cfg)
    sched.register("t1", 0, lambda: None)
    results = sched.check_and_run()
    assert results["t1"]["success"] is True
