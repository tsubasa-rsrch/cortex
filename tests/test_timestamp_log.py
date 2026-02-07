"""Tests for the timestamp log."""

from cortex import TimestampLog, CortexConfig


def test_start_and_end(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    tl = TimestampLog(config=cfg)
    start = tl.start_task("test task")
    assert start["task"] == "test task"
    result = tl.end_task("done")
    assert result["task"] == "test task"
    assert result["elapsed_min"] >= 0


def test_checkpoint(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    tl = TimestampLog(config=cfg)
    tl.start_task("task")
    cp = tl.checkpoint("halfway")
    assert cp is not None
    assert cp["note"] == "halfway"


def test_checkpoint_without_task(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    tl = TimestampLog(config=cfg)
    assert tl.checkpoint() is None


def test_end_without_task(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    tl = TimestampLog(config=cfg)
    assert tl.end_task() is None


def test_auto_end_previous(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    tl = TimestampLog(config=cfg)
    tl.start_task("task1")
    tl.start_task("task2")  # auto-ends task1
    status = tl.get_status()
    assert status["current_task"]["name"] == "task2"


def test_get_status(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    tl = TimestampLog(config=cfg)
    status = tl.get_status()
    assert "current_time" in status
    assert status["current_task"] is None


def test_persistence(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    tl1 = TimestampLog(config=cfg)
    tl1.start_task("persistent task")

    tl2 = TimestampLog(config=cfg)
    status = tl2.get_status()
    assert status["current_task"]["name"] == "persistent task"
