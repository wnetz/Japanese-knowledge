from pathlib import Path


def test_app_defaults_to_upcoming_reviews() -> None:
    source = Path("gui/app.py").read_text(encoding="utf-8")
    assert 'self.show_screen("reviews")' in source


def test_upcoming_review_defaults() -> None:
    source = Path("gui/reviews_screen.py").read_text(encoding="utf-8")

    assert 'self.review_anki_var = tk.BooleanVar(value=True)' in source
    assert 'self.review_wanikani_var = tk.BooleanVar(value=True)' in source
    assert 'self.review_bunpro_var = tk.BooleanVar(value=True)' in source
    assert 'self.review_writing_var = tk.BooleanVar(value=True)' in source
    assert 'self.review_horizon_var = tk.StringVar(value="24 hours")' in source
    assert 'self.new_only_var = tk.BooleanVar(value=True)' in source
