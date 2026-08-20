from pathlib import Path

from config.loader import load_config


def test_default_project_cooldown_range_loads():
    config = load_config()
    assert config.writing.new_fail_cooldown_min == 3
    assert config.writing.new_fail_cooldown_max == 5
    assert config.writing.new_fail_cooldown_min <= config.writing.new_fail_cooldown_max
