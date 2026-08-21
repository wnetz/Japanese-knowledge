import json
from pathlib import Path


def test_grammar_source_indexes_and_merged_profile_exist() -> None:
    assert Path("output/auto/grammar_index.json").exists()
    assert Path("output/auto/textbook_index.json").exists()
    assert Path("output/manual/grammar_use_index.json").exists()
    assert Path("output/manual/grammar_aliases.json").exists()
    assert Path("output/auto/grammar_alias_candidates.json").exists()
    assert Path("output/auto/grammar_profile.json").exists()


def test_portable_project_does_not_keep_legacy_grammar_output_names() -> None:
    assert not Path("output/auto/textbook_profile.json").exists()
    assert not Path("output/manual/grammar_mastery.json").exists()


def test_knowledge_profile_uses_merged_grammar_profile() -> None:
    data = json.loads(
        Path("output/knowledge_profile.json").read_text(encoding="utf-8")
    )
    assert set(data) == {"grammar_profile", "vocabulary_profile"}
    assert "items" in data["grammar_profile"]


def test_alias_file_is_manual_and_candidates_are_generated() -> None:
    aliases = json.loads(
        Path("output/manual/grammar_aliases.json").read_text(encoding="utf-8")
    )
    candidates = json.loads(
        Path("output/auto/grammar_alias_candidates.json").read_text(encoding="utf-8")
    )
    assert aliases["schema_version"] == 1
    assert isinstance(aliases["aliases"], list)
    assert candidates["schema_version"] == 1
    assert isinstance(candidates["candidates"], list)
