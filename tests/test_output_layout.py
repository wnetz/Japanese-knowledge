from pathlib import Path
from config.loader import load_config
from gui.shared import (
    VOCABULARY_PROFILE_PATH, WRITING_PROFILE_PATH,
    ANKI_INDEX_PATH, WANIKANI_INDEX_PATH, BUNPRO_PRIMARY_PATH,
)


def test_config_output_layout():
    c = load_config()
    assert c.output.anki_index == "auto/anki_index.json"
    assert c.output.grammar_index == "auto/grammar_index.json"
    assert c.output.grammar_profile == "auto/grammar_profile.json"
    assert c.output.profile_manifest == "auto/profile_manifest.json"
    assert c.output.textbook_index == "auto/textbook_index.json"
    assert c.output.vocabulary_profile == "auto/vocabulary_profile.json"
    assert c.output.wanikani_index == "auto/wanikani_index.json"
    assert c.output.writing_profile == "manual/writing_profile.json"
    assert c.output.srs_history == "manual/srs_history.json"
    assert c.output.grammar_use_index == "manual/grammar_use_index.json"
    assert c.output.grammar_aliases == "manual/grammar_aliases.json"
    assert c.output.grammar_alias_candidates == "auto/grammar_alias_candidates.json"
    assert c.output.knowledge_profile == "knowledge_profile.json"


def test_gui_output_layout():
    assert VOCABULARY_PROFILE_PATH.parts[-2:] == ("auto", "vocabulary_profile.json")
    assert WRITING_PROFILE_PATH.parts[-2:] == ("manual", "writing_profile.json")
    assert ANKI_INDEX_PATH.parts[-2:] == ("auto", "anki_index.json")
    assert WANIKANI_INDEX_PATH.parts[-2:] == ("auto", "wanikani_index.json")
    assert BUNPRO_PRIMARY_PATH.parts[-2:] == ("auto", "grammar_index.json")
