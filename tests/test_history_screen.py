from pathlib import Path


def test_app_has_srs_history_page() -> None:
    source = Path("gui/app.py").read_text(encoding="utf-8")
    assert "HistoryScreen" in source
    assert 'text="SRS History"' in source
    assert 'self.frames["history"]' in source


def test_history_screen_has_requested_sources_and_dropdowns() -> None:
    source = Path("gui/history_screen.py").read_text(encoding="utf-8")
    assert '("wanikani", "WaniKani")' in source
    assert '("anki", "Anki")' in source
    assert '("bunpro", "Bunpro")' in source
    assert '("writing", "Writing")' in source
    assert '"kana_vocabulary"' in source
    assert '"radical"' in source
    assert '"vocabulary"' in source
    assert '"kanji"' in source
    assert 'available_anki_decks(self.history)' in source
    assert '["Total", "N5", "N4", "N3", "N2", "N1"]' in source


def test_bunpro_has_content_type_selector_defaulting_to_grammar() -> None:
    source = Path("gui/history_screen.py").read_text(encoding="utf-8")
    assert 'self.bunpro_type_var = tk.StringVar(value="Grammar")' in source
    assert 'values=["Grammar", "Vocabulary", "Both"]' in source
    assert 'bunpro_content_type=self.bunpro_type_var.get().lower()' in source


def test_anki_new_toggle_defaults_off() -> None:
    source = Path("gui/history_screen.py").read_text(encoding="utf-8")
    assert 'self.anki_include_new_var = tk.BooleanVar(value=False)' in source
    assert 'text="Include New"' in source
    assert 'and stage == "new"' in source


def test_history_graph_uses_japanese_capable_font_for_titles() -> None:
    source = Path("gui/history_screen.py").read_text(encoding="utf-8")
    assert 'fontfamily="Yu Gothic UI"' in source
