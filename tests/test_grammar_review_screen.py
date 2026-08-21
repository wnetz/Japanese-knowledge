from pathlib import Path


def test_app_has_grammar_review_page() -> None:
    source = Path("gui/app.py").read_text(encoding="utf-8")
    assert "GrammarReviewScreen" in source
    assert 'text="Grammar Review"' in source
    assert 'self.frames["grammar_review"]' in source


def test_manual_grammar_mastery_path_is_protected() -> None:
    source = Path("gui/shared.py").read_text(encoding="utf-8")
    assert 'GRAMMAR_MASTERY_PATH = MANUAL_OUTPUT_DIR / "grammar_mastery.json"' in source


def test_save_review_button_is_in_pending_controls() -> None:
    source = Path("gui/grammar_review_screen.py").read_text(encoding="utf-8")
    pending_index = source.index("pending_buttons = ttk.Frame(pending_box)")
    save_index = source.index('text="Save Review"')
    details_index = source.index('text="Optional review context"')

    assert pending_index < save_index < details_index
    assert source.count('text="Save Review"') == 1
