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


def test_push_returns_notification(tmp_path):
    """push() returns the notification dict."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg)
    n = nq.push("alert", "Fire!", priority="urgent")
    assert n["type"] == "alert"
    assert n["message"] == "Fire!"
    assert n["priority"] == "urgent"
    assert n["read"] is False
    assert "timestamp" in n


def test_push_with_data(tmp_path):
    """push() stores extra data."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg)
    n = nq.push("info", "test", data={"key": "value"})
    assert n["data"]["key"] == "value"


def test_get_latest_empty(tmp_path):
    """get_latest() returns None when no notifications."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg)
    assert nq.get_latest() is None


def test_format_with_explicit_list(tmp_path):
    """format() accepts explicit notification list."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg)
    notifs = [{"type": "info", "message": "Hello", "priority": "normal", "timestamp": "2026-01-01T12:00:00"}]
    output = nq.format(notifs)
    assert "Hello" in output


def test_corrupt_queue_file(tmp_path):
    """Corrupt queue file doesn't crash."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg)
    nq._queue_file.parent.mkdir(parents=True, exist_ok=True)
    nq._queue_file.write_text("{not valid json!!!")
    assert nq.get_unread() == []


def test_corrupt_latest_file(tmp_path):
    """Corrupt latest file returns None."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    nq = NotificationQueue(config=cfg)
    nq._latest_file.parent.mkdir(parents=True, exist_ok=True)
    nq._latest_file.write_text("BROKEN")
    assert nq.get_latest() is None
