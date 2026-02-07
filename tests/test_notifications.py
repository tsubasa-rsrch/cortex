"""Tests for the notification queue."""

from cortex import NotificationQueue, CortexConfig


def test_push_and_get_unread(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg)
    nq.push("message", "Hello")
    unread = nq.get_unread()
    assert len(unread) == 1
    assert unread[0]["message"] == "Hello"


def test_mark_all_read(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg)
    nq.push("alert", "Fire!")
    nq.push("info", "Update")
    nq.mark_all_read()
    assert len(nq.get_unread()) == 0


def test_get_latest(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg)
    nq.push("info", "First")
    nq.push("info", "Second")
    latest = nq.get_latest()
    assert latest["message"] == "Second"


def test_max_queue(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg, max_queue=5)
    for i in range(10):
        nq.push("info", f"msg {i}")
    queue = nq._load_queue()
    assert len(queue) == 5


def test_format_output(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg)
    nq.push("message", "Test notification", priority="high")
    output = nq.format()
    assert "Test notification" in output
    assert "Notifications (1)" in output


def test_format_empty(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg)
    assert nq.format() == "No notifications"


def test_custom_icons(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg, icons={"custom": "X"})
    nq.push("custom", "Custom type")
    output = nq.format()
    assert "X" in output
