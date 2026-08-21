from gui.style import (
    ANKI_STAGE_STYLES,
    BUNPRO_STAGE_STYLES,
    WANIKANI_STAGE_STYLES,
)


def test_wanikani_runs_low_to_high_toward_dark_purple() -> None:
    assert WANIKANI_STAGE_STYLES["apprentice_1"]["color"] == "#ef5350"
    assert WANIKANI_STAGE_STYLES["apprentice_2"]["color"] == "#ff8c42"
    assert WANIKANI_STAGE_STYLES["apprentice_3"]["color"] == "#f4d35e"
    assert WANIKANI_STAGE_STYLES["apprentice_4"]["color"] == "#42c77a"
    assert WANIKANI_STAGE_STYLES["guru_2"]["color"] == "#4a90e2"
    assert WANIKANI_STAGE_STYLES["burned"]["color"] == "#4b237a"


def test_anki_stage_colors() -> None:
    assert ANKI_STAGE_STYLES["new"]["color"] == "#26d9d9"
    assert ANKI_STAGE_STYLES["learning"]["color"] == "#42c77a"
    assert ANKI_STAGE_STYLES["review"]["color"] == "#ef5350"
    assert ANKI_STAGE_STYLES["relearning"]["color"] == "#d0d0d0"


def test_bunpro_special_lines() -> None:
    assert BUNPRO_STAGE_STYLES["beginner"]["color"] == "#ef5350"
    assert BUNPRO_STAGE_STYLES["master"]["color"] == "#7e57c2"
    assert BUNPRO_STAGE_STYLES["ghost"]["color"] == "#ffffff"
    assert BUNPRO_STAGE_STYLES["ghost"]["linestyle"] == ":"
    assert BUNPRO_STAGE_STYLES["self_study"]["color"] == "#9e9e9e"


def test_history_screen_imports_styles_instead_of_defining_them() -> None:
    from pathlib import Path

    source = Path("gui/history_screen.py").read_text(encoding="utf-8")
    assert "from .style import (" in source
    assert "WANIKANI_STAGE_STYLES = {" not in source
    assert "ANKI_STAGE_STYLES = {" not in source
    assert "BUNPRO_STAGE_STYLES = {" not in source
