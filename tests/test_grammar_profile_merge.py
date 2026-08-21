import json
from pathlib import Path

from grammar.profile import GrammarProfileBuilder


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_profile_merges_exact_use_item_into_existing_source_item(tmp_path: Path) -> None:
    write(
        tmp_path / "auto/grammar_index.json",
        {"grammar": [{"id": 1, "title": "～たい", "meaning": "want to"}]},
    )
    write(
        tmp_path / "auto/textbook_index.json",
        {"conjugations": [], "lessons": []},
    )
    write(
        tmp_path / "manual/grammar_use_index.json",
        {
            "items": {
                "～たい": {
                    "item_id": "～たい",
                    "grammar": "～たい",
                    "attempts": 2,
                    "average_score": 2.0,
                }
            }
        },
    )
    write(tmp_path / "manual/grammar_aliases.json", {"schema_version": 1, "aliases": []})

    profile = GrammarProfileBuilder(tmp_path).build()

    item = profile["items"]["grammar::～たい"]
    assert item["sources"]["bunpro"]["id"] == 1
    assert item["use"]["attempts"] == 2
    assert item["aliases"]["bunpro"] == ["～たい"]
    assert item["aliases"]["grammar_use"] == ["～たい"]


def test_textbook_patterns_and_skills_become_items_with_lessons(tmp_path: Path) -> None:
    write(tmp_path / "auto/grammar_index.json", {"grammar": []})
    write(
        tmp_path / "auto/textbook_index.json",
        {
            "conjugations": [{"name": "た形", "forms": {"past": "た"}}],
            "lessons": [
                {
                    "id": "1-1",
                    "practice": {
                        "patterns": ["#～ たいです"],
                        "skills": ["[[た形動詞]]"],
                    },
                }
            ],
        },
    )
    write(tmp_path / "manual/grammar_use_index.json", {"items": {}})
    write(tmp_path / "manual/grammar_aliases.json", {"schema_version": 1, "aliases": []})

    profile = GrammarProfileBuilder(tmp_path).build()

    assert "conjugation::た形" in profile["items"]
    assert profile["items"]["pattern::#～ たいです"]["lessons"] == ["1-1"]
    assert profile["items"]["skill::[[た形動詞]]"]["lessons"] == ["1-1"]


def test_manual_source_aware_alias_controls_merge(tmp_path: Path) -> None:
    write(
        tmp_path / "auto/grammar_index.json",
        {"grammar": [{"id": 59, "title": "たい", "meaning": "Want to do"}]},
    )
    write(tmp_path / "auto/textbook_index.json", {"conjugations": [], "lessons": []})
    write(
        tmp_path / "manual/grammar_use_index.json",
        {
            "items": {
                "～たい": {
                    "item_id": "～たい",
                    "grammar": "～たい",
                    "attempts": 1,
                    "average_score": 3.0,
                }
            }
        },
    )
    write(
        tmp_path / "manual/grammar_aliases.json",
        {
            "schema_version": 1,
            "aliases": [
                {
                    "source": "grammar_use",
                    "value": "～たい",
                    "canonical_id": "grammar::たい",
                }
            ],
        },
    )

    profile = GrammarProfileBuilder(tmp_path).build()

    assert "grammar::たい" in profile["items"]
    assert profile["items"]["grammar::たい"]["use"]["attempts"] == 1
    assert "observed::～たい" not in profile["items"]


def test_unknown_use_item_is_preserved(tmp_path: Path) -> None:
    write(tmp_path / "auto/grammar_index.json", {"grammar": []})
    write(tmp_path / "auto/textbook_index.json", {"conjugations": [], "lessons": []})
    write(
        tmp_path / "manual/grammar_use_index.json",
        {
            "items": {
                "分かる": {
                    "item_id": "分かる",
                    "grammar": "分かる",
                    "attempts": 1,
                    "average_score": 3.0,
                },
                "particle::に": {
                    "item_id": "particle::に",
                    "grammar": "particle::に",
                    "attempts": 1,
                    "average_score": 1.0,
                },
            }
        },
    )
    write(tmp_path / "manual/grammar_aliases.json", {"schema_version": 1, "aliases": []})

    profile = GrammarProfileBuilder(tmp_path).build()

    assert "observed::分かる" in profile["items"]
    assert "particle::に" in profile["items"]


def test_conjugation_items_inherit_lessons_from_skill_references(tmp_path: Path) -> None:
    write(tmp_path / "auto/grammar_index.json", {"grammar": []})
    write(
        tmp_path / "auto/textbook_index.json",
        {
            "conjugations": [
                {"name": "た形", "forms": {"past": "た"}},
                {"name": "ます形", "forms": {"non_past": "ます"}},
            ],
            "lessons": [
                {
                    "id": "4-2",
                    "practice": {
                        "skills": ["[[ます形動詞]] #past and #present_negative"]
                    },
                },
                {
                    "id": "8-1",
                    "practice": {
                        "skills": ["[[た形動詞]]"]
                    },
                },
            ],
        },
    )
    write(tmp_path / "manual/grammar_use_index.json", {"items": {}})
    write(tmp_path / "manual/grammar_aliases.json", {"schema_version": 1, "aliases": []})

    profile = GrammarProfileBuilder(tmp_path).build()

    assert profile["items"]["conjugation::ます形"]["lessons"] == ["4-2"]
    assert profile["items"]["conjugation::た形"]["lessons"] == ["8-1"]


def test_alias_candidate_uses_textbook_grammar_head(tmp_path: Path) -> None:
    write(tmp_path / "auto/grammar_index.json", {"grammar": []})
    write(
        tmp_path / "auto/textbook_index.json",
        {
            "conjugations": [],
            "lessons": [
                {
                    "id": "15-1",
                    "practice": {
                        "patterns": ["#～ ば、 #∵"],
                        "skills": [],
                    },
                }
            ],
        },
    )
    write(
        tmp_path / "manual/grammar_use_index.json",
        {
            "items": {
                "～ば": {
                    "item_id": "～ば",
                    "grammar": "～ば",
                    "attempts": 1,
                    "average_score": 2.0,
                }
            }
        },
    )
    write(tmp_path / "manual/grammar_aliases.json", {"schema_version": 1, "aliases": []})

    builder = GrammarProfileBuilder(tmp_path)
    builder.build()

    candidates = json.loads(
        (tmp_path / "auto/grammar_alias_candidates.json").read_text(encoding="utf-8")
    )["candidates"]

    candidate = next(
        entry
        for entry in candidates
        if entry["source"] == "grammar_use" and entry["value"] == "～ば"
    )

    assert any(
        match["canonical_id"] == "pattern::#～ ば、 #∵"
        for match in candidate["suggested_matches"]
    )


def test_manual_alias_can_use_values_list(tmp_path: Path) -> None:
    write(
        tmp_path / "auto/grammar_index.json",
        {"grammar": [{"id": 1, "title": "～たい"}]},
    )
    write(tmp_path / "auto/textbook_index.json", {"conjugations": [], "lessons": []})
    write(
        tmp_path / "manual/grammar_use_index.json",
        {
            "items": {
                "たい": {"grammar": "たい", "attempts": 1},
                "～たいです": {"grammar": "～たいです", "attempts": 2},
            }
        },
    )
    write(
        tmp_path / "manual/grammar_aliases.json",
        {
            "schema_version": 1,
            "aliases": [
                {
                    "source": "grammar_use",
                    "values": ["たい", "～たいです"],
                    "canonical_id": "grammar::～たい",
                }
            ],
        },
    )

    profile = GrammarProfileBuilder(tmp_path).build()

    item = profile["items"]["grammar::～たい"]
    assert item["aliases"]["grammar_use"] == ["たい", "～たいです"]
    assert "observed::たい" not in profile["items"]
    assert "observed::～たいです" not in profile["items"]


def test_manual_alias_value_and_values_are_backward_compatible(tmp_path: Path) -> None:
    write(tmp_path / "auto/grammar_index.json", {"grammar": []})
    write(tmp_path / "auto/textbook_index.json", {"conjugations": [], "lessons": []})
    write(tmp_path / "manual/grammar_use_index.json", {"items": {}})
    write(
        tmp_path / "manual/grammar_aliases.json",
        {
            "schema_version": 1,
            "aliases": [
                {
                    "source": "grammar_use",
                    "value": "～ば",
                    "values": ["～ば", "ば"],
                    "canonical_id": "pattern::#～ ば、 #∵",
                }
            ],
        },
    )

    from grammar.profile import load_aliases
    aliases = load_aliases(tmp_path / "manual/grammar_aliases.json")

    assert aliases == [
        {
            "source": "grammar_use",
            "value": "～ば",
            "canonical_id": "pattern::#～ ば、 #∵",
        },
        {
            "source": "grammar_use",
            "value": "ば",
            "canonical_id": "pattern::#～ ば、 #∵",
        },
    ]
