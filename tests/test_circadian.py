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
