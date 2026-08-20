from pathlib import Path


def test_update_screen_allows_rebuild_with_no_external_sources() -> None:
    source = Path("gui/update_screen.py").read_text(encoding="utf-8")

    assert "Select at least one of Anki, WaniKani, or Bunpro." not in source
    assert "Rebuilding profiles from existing source data..." in source
    assert "Selected: none — rebuild only" in source


def test_empty_sources_argument_is_supported_by_update_profile() -> None:
    source = Path("update_profile.py").read_text(encoding="utf-8")

    # Empty --sources produces an empty selected_sources set; the script then
    # skips Anki/WaniKani/Bunpro refreshes and continues building profiles.
    assert "selected_sources = {" in source
    assert 'config.wanikani.enabled and "wanikani" in selected_sources' in source
    assert 'config.anki.enabled and "anki" in selected_sources' in source
    assert 'config.bunpro.enabled and "bunpro" in selected_sources' in source
    assert 'progress("Profile: building vocabulary profile...")' in source
