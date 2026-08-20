from pathlib import Path


def test_writing_screen_has_explicit_no_reviews_state() -> None:
    source = Path("gui/writing_screen.py").read_text(encoding="utf-8")
    assert "def _show_no_reviews_state" in source
    assert 'self.target_var.set("No writing reviews due")' in source
    assert "self.quiz_stats_var.set(\"You're caught up.\")" in source
    assert "self._show_no_reviews_state()" in source
