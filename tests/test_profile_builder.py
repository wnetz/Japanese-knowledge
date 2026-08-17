from pathlib import Path
import json

from profile import ProfileBuilder


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_builder_merges_wanikani_and_anki_and_ignores_obsidian(tmp_path: Path) -> None:
    _write(tmp_path / "wanikani_index.json", {
        "subjects": [{
            "id": 1,
            "subject_type": "vocabulary",
            "characters": "食べる",
            "readings": [{"reading": "たべる", "primary": True, "accepted_answer": True}],
            "meanings": [{"meaning": "To Eat"}],
            "parts_of_speech": {"normalized": ["ichidan verb"]},
            "assignment": {"srs_stage": 0, "started_at": None},
            "review_statistics": {},
        }]
    })
    _write(tmp_path / "anki_index.json", {
        "notes": [{
            "word": "食べる",
            "reading": "たべる",
            "meanings": ["eat"],
            "study": {"reviews": 10, "best_interval": 60, "lapses": 0, "ease": 2.5, "last_reviewed": "2026-07-14", "state": "review"},
        }]
    })
    # This file may coexist in the output folder, but it is intentionally not
    # consumed by the vocabulary profile builder.
    _write(tmp_path / "textbook_profile.json", {
        "notes": [{"groups": [{"members": [{"word": "飲む", "reading": "のむ"}]}]}]
    })

    builder = ProfileBuilder(tmp_path)
    profile = builder.build()

    assert len(profile.vocabulary) == 1
    item = profile.vocabulary[0]
    assert item.sources == {"anki", "wanikani"}
    assert item.reading == "たべる"
    assert item.confidence is not None
    assert profile.metadata.sources == ["wanikani", "anki"]

    # Unstudied WaniKani is ignored, so the score is exactly the Anki score.
    from profile.scoring import score_anki
    assert item.confidence == score_anki(item.study["anki"])


def test_builder_writes_vocabulary_profile_by_default(tmp_path: Path) -> None:
    _write(tmp_path / "anki_index.json", {
        "notes": [{
            "word": "猫",
            "reading": "ねこ",
            "meanings": ["cat"],
            "study": {"reviews": 0, "best_interval": 0, "state": "new"},
        }]
    })

    builder = ProfileBuilder(tmp_path)
    profile = builder.build_and_write()

    assert builder.output_path.name == "vocabulary_profile.json"
    assert builder.output_path.exists()
    written = json.loads(builder.output_path.read_text(encoding="utf-8"))
    assert set(written) == {"metadata", "vocabulary"}
    assert written["vocabulary"][0]["word"] == "猫"
    assert profile.metadata.confidence_scored_count == 0


def test_final_json_contains_only_compact_study_fields(tmp_path: Path) -> None:
    _write(tmp_path / "wanikani_index.json", {
        "subjects": [{
            "id": 1,
            "subject_type": "vocabulary",
            "characters": "食べる",
            "readings": [{"reading": "たべる", "primary": True, "accepted_answer": True}],
            "meanings": [{"meaning": "To Eat"}],
            "parts_of_speech": {"normalized": ["ichidan verb"]},
            "assignment": {
                "srs_stage": 7,
                "unlocked_at": "2026-01-01T00:00:00Z",
                "started_at": "2026-01-02T00:00:00Z",
                "passed_at": "2026-01-03T00:00:00Z",
                "burned_at": None,
            },
            "review_statistics": {"percentage_correct": 90},
        }]
    })
    _write(tmp_path / "anki_index.json", {
        "notes": [{
            "word": "食べる",
            "reading": "たべる",
            "meanings": ["eat"],
            "pitch_accent": "LHH",
            "frequency": 100,
            "study": {
                "reviews": 37,
                "best_interval": 120,
                "lapses": 2,
                "ease": 2.45,
                "last_reviewed": "2026-07-14",
                "state": "review",
            },
        }]
    })

    builder = ProfileBuilder(tmp_path)
    builder.build_and_write()
    written = json.loads(builder.output_path.read_text(encoding="utf-8"))
    assert "schema_version" not in written["metadata"]
    item = written["vocabulary"][0]
    assert "pitch_accents" not in item
    assert "frequency" not in item
    assert "source_ids" not in item
    assert item["study"]["wanikani"] == {"srs_stage": 7}
    assert item["study"]["anki"] == {
        "reviews": 37,
        "ease": 2.45,
        "last_reviewed": "2026-07-14",
    }
