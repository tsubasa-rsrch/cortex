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


def test_data_dir_created_on_init(tmp_path):
    """data_dir is created if it doesn't exist."""
    new_dir = tmp_path / "brand_new"
    assert not new_dir.exists()
    cfg = CortexConfig(data_dir=new_dir)
    assert new_dir.exists()


def test_state_file_nested(tmp_path):
    """state_file works with subdirectory paths."""
    cfg = CortexConfig(data_dir=tmp_path)
    path = cfg.state_file("sub/dir/file.json")
    assert path == tmp_path / "sub" / "dir" / "file.json"


def test_string_data_dir_converted(tmp_path):
    """String data_dir is converted to Path."""
    cfg = CortexConfig(data_dir=str(tmp_path), name="test")
    assert isinstance(cfg.data_dir, Path)
