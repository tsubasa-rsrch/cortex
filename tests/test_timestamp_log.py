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


def test_end_task_returns_checkpoints_count(tmp_path):
    """end_task includes number of checkpoints."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    tl = TimestampLog(config=cfg)
    tl.start_task("task")
    tl.checkpoint("cp1")
    tl.checkpoint("cp2")
    result = tl.end_task("finished")
    assert result["checkpoints"] == 2


def test_auto_end_creates_entry(tmp_path):
    """Starting new task auto-ends previous and creates entry."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    tl = TimestampLog(config=cfg)
    tl.start_task("first")
    tl.start_task("second")
    # Should have: start(first), end(first/auto), start(second)
    assert len(tl._data["entries"]) == 3
    assert tl._data["entries"][1]["type"] == "end"
    assert "(auto-ended)" in tl._data["entries"][1]["note"]


def test_status_recent_entries(tmp_path):
    """get_status shows recent entries (max 5)."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    tl = TimestampLog(config=cfg)
    for i in range(8):
        tl.start_task(f"task_{i}")
        tl.end_task()
    status = tl.get_status()
    assert len(status["recent_entries"]) == 5


def test_status_with_active_task(tmp_path):
    """get_status shows active task details."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    tl = TimestampLog(config=cfg)
    tl.start_task("active")
    status = tl.get_status()
    assert status["current_task"] is not None
    assert status["current_task"]["name"] == "active"
    assert "elapsed_min" in status["current_task"]


def test_corrupt_state_file(tmp_path):
    """Corrupt state file doesn't crash."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    state_file = cfg.state_file("timestamp_log.json")
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("NOT JSON{{{")
    tl = TimestampLog(config=cfg)
    start = tl.start_task("recovery")
    assert start["task"] == "recovery"
