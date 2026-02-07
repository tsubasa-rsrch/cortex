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
