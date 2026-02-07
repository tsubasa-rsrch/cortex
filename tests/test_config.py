"""Tests for the configuration module."""

from pathlib import Path
from cortex import CortexConfig, get_config, set_config


def test_default_config():
    cfg = CortexConfig()
    assert cfg.data_dir == Path.home() / ".cortex"
    assert cfg.name == "agent"


def test_custom_config(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path / "custom", name="my-bot")
    assert cfg.name == "my-bot"
    assert cfg.data_dir.exists()


def test_state_file(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path)
    path = cfg.state_file("test.json")
    assert path == tmp_path / "test.json"


def test_global_config(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="global-test")
    set_config(cfg)
    assert get_config().name == "global-test"
    # Reset
    set_config(CortexConfig())
