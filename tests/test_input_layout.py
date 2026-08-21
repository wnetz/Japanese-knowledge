from pathlib import Path
import json


def test_source_adapters_are_consolidated_under_input() -> None:
    root = Path(".")
    for source in ("anki", "wanikani", "bunpro", "obsidian"):
        assert (root / "input" / source / "__init__.py").exists()

    assert not (root / "importers").exists()
    assert not (root / "anki").exists()
    assert not (root / "wanikani").exists()
    assert not (root / "obsidian").exists()


def test_config_has_no_source_enabled_switches() -> None:
    config = json.loads(Path("config.json").read_text(encoding="utf-8"))
    for section in ("anki", "wanikani", "bunpro", "obsidian"):
        assert "enabled" not in config[section]


def test_update_profile_imports_sources_from_input_package() -> None:
    source = Path("update_profile.py").read_text(encoding="utf-8")
    assert "from input.anki import AnkiImporter" in source
    assert "from input.bunpro import BunproImporter" in source
    assert "from input.obsidian import TextbookIndexImporter" in source
    assert "from input.wanikani import WaniKaniImporter" in source
    assert "importers." not in source
