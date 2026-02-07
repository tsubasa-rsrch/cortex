"""Tests for the circadian rhythm system."""

from cortex import CircadianRhythm, CircadianMode, CortexConfig


def test_mode_detection(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    cr = CircadianRhythm(config=cfg)
    result = cr.check_and_update()
    assert result["mode"] in list(CircadianMode)
    assert result["changed"] is True  # first call always changes


def test_no_change_on_second_call(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    cr = CircadianRhythm(config=cfg)
    cr.check_and_update()
    result2 = cr.check_and_update()
    assert result2["changed"] is False


def test_custom_suggestions(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    custom = {"morning": [{"type": "custom", "message": "Do stuff", "priority": "high"}]}
    cr = CircadianRhythm(config=cfg, suggestions=custom)
    cr.check_and_update()
    if cr.current_mode == CircadianMode.MORNING:
        suggestions = cr.get_current_suggestions()
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "custom"


def test_get_status(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    cr = CircadianRhythm(config=cfg)
    status = cr.get_status()
    assert "mode" in status
    assert "energy_level" in status


def test_state_persistence(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    cr1 = CircadianRhythm(config=cfg)
    cr1.check_and_update()
    mode1 = cr1.current_mode

    cr2 = CircadianRhythm(config=cfg)
    assert cr2.current_mode == mode1


def test_hour_to_mode_mapping(tmp_path):
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    cr = CircadianRhythm(config=cfg)
    assert cr._get_mode_for_hour(8) == CircadianMode.MORNING
    assert cr._get_mode_for_hour(14) == CircadianMode.AFTERNOON
    assert cr._get_mode_for_hour(20) == CircadianMode.EVENING
    assert cr._get_mode_for_hour(3) == CircadianMode.NIGHT


def test_hour_boundaries(tmp_path):
    """Exact boundary hours map correctly."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    cr = CircadianRhythm(config=cfg)
    assert cr._get_mode_for_hour(0) == CircadianMode.NIGHT
    assert cr._get_mode_for_hour(5) == CircadianMode.NIGHT
    assert cr._get_mode_for_hour(6) == CircadianMode.MORNING
    assert cr._get_mode_for_hour(11) == CircadianMode.MORNING
    assert cr._get_mode_for_hour(12) == CircadianMode.AFTERNOON
    assert cr._get_mode_for_hour(17) == CircadianMode.AFTERNOON
    assert cr._get_mode_for_hour(18) == CircadianMode.EVENING
    assert cr._get_mode_for_hour(23) == CircadianMode.EVENING


def test_get_current_activities(tmp_path):
    """Activities are returned for the current mode."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    activities = {"morning": ["check X", "read news"], "afternoon": ["code"]}
    cr = CircadianRhythm(config=cfg, activities=activities)
    result = cr.get_current_activities()
    assert isinstance(result, list)


def test_custom_activities(tmp_path):
    """Custom activities are used when provided."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    custom = {"morning": ["meditate"], "afternoon": ["focus"], "evening": ["journal"], "night": ["sleep"]}
    cr = CircadianRhythm(config=cfg, activities=custom)
    cr.check_and_update()
    acts = cr.get_current_activities()
    assert isinstance(acts, list)
    mode_name = cr.current_mode.value
    assert acts == custom[mode_name]


def test_mode_change_records_old_mode(tmp_path):
    """First mode change records old_mode as None."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    cr = CircadianRhythm(config=cfg)
    result = cr.check_and_update()
    assert result["changed"] is True
    assert result["old_mode"] is None


def test_mode_history_appended(tmp_path):
    """Mode history grows on changes."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    cr = CircadianRhythm(config=cfg)
    cr.check_and_update()
    assert len(cr.mode_history) >= 1
    entry = cr.mode_history[-1]
    assert "from" in entry
    assert "to" in entry
    assert "timestamp" in entry


def test_all_modes_have_metadata(tmp_path):
    """All four CircadianModes have metadata."""
    from cortex.circadian import _DEFAULT_MODE_META
    for mode in CircadianMode:
        assert mode in _DEFAULT_MODE_META
        meta = _DEFAULT_MODE_META[mode]
        assert "name" in meta
        assert "icon" in meta
        assert "energy_level" in meta


def test_corrupt_state_file(tmp_path):
    """Corrupt state file doesn't crash, just resets."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    state_file = cfg.state_file("circadian_state.json")
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("NOT VALID JSON{{{")
    cr = CircadianRhythm(config=cfg)
    result = cr.check_and_update()
    assert result["mode"] in list(CircadianMode)


def test_status_has_all_fields(tmp_path):
    """get_status returns all expected fields."""
    cfg = CortexConfig(data_dir=tmp_path, name="test")
    cr = CircadianRhythm(config=cfg)
    status = cr.get_status()
    for key in ["mode", "name", "icon", "description", "energy_level", "last_change", "activities"]:
        assert key in status
