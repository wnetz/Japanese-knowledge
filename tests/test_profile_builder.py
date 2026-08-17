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

    # Unstudied WaniKani is ignored. The 60-day Anki interval establishes
    # the configured 0.75 confidence floor.
    assert item.confidence == 0.75


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
        "interval": 120,
        "last_reviewed": "2026-07-14",
    }


def test_builder_merges_migaku_known_words_and_scores_them(tmp_path: Path) -> None:
    _write(tmp_path / "wanikani_index.json", {
        "subjects": [{
            "id": 1,
            "subject_type": "kana_vocabulary",
            "characters": "コーヒー",
            "readings": [],
            "meanings": [{"meaning": "Coffee"}],
            "parts_of_speech": {"normalized": ["noun"]},
            "assignment": {"srs_stage": 0, "started_at": None},
            "review_statistics": {},
        }]
    })
    _write(tmp_path / "migaku_known_words.json", {
        "words": [{
            "word": "コーヒー",
            "reading": "こーひー",
            "language": "ja",
            "status": "KNOWN",
        }, {
            "word": "猫",
            "reading": "ねこ",
            "language": "ja",
            "status": "KNOWN",
        }]
    })

    builder = ProfileBuilder(tmp_path)
    profile = builder.build()

    assert len(profile.vocabulary) == 2
    coffee = next(item for item in profile.vocabulary if item.word == "コーヒー")
    cat = next(item for item in profile.vocabulary if item.word == "猫")

    assert coffee.sources == {"wanikani", "migaku"}
    assert coffee.study["migaku"].status == "KNOWN"
    assert cat.sources == {"migaku"}
    assert cat.confidence == 0.6
    assert profile.metadata.sources == ["wanikani", "migaku"]
    assert profile.metadata.source_counts["migaku"] == 2


def test_migaku_different_real_readings_remain_separate(tmp_path: Path) -> None:
    _write(tmp_path / "wanikani_index.json", {
        "subjects": [{
            "id": 1,
            "subject_type": "vocabulary",
            "characters": "日本",
            "readings": [{"reading": "にっぽん", "primary": True, "accepted_answer": True}],
            "meanings": [{"meaning": "Japan"}],
            "parts_of_speech": {"normalized": ["proper noun"]},
            "assignment": {"srs_stage": 0, "started_at": None},
            "review_statistics": {},
        }]
    })
    _write(tmp_path / "migaku_known_words.json", {
        "words": [{
            "word": "日本",
            "reading": "にほん",
            "language": "ja",
            "status": "KNOWN",
        }]
    })

    profile = ProfileBuilder(tmp_path).build()
    assert len(profile.vocabulary) == 2
    assert {item.reading for item in profile.vocabulary} == {"にっぽん", "にほん"}

def test_writable_tag_requires_all_kanji_to_be_writable(tmp_path: Path) -> None:
    _write(tmp_path / "writable_kanji.json", {
        "writable_kanji": [
            {"character": "日", "example_words": ["日本"]},
            {"character": "本", "example_words": ["日本"]},
            {"character": "人", "example_words": ["日本人"]},
        ]
    })
    _write(tmp_path / "wanikani_index.json", {
        "subjects": [
            {
                "id": 1,
                "subject_type": "vocabulary",
                "characters": "日本人",
                "readings": [{"reading": "にほんじん", "primary": True, "accepted_answer": True}],
                "meanings": [{"meaning": "Japanese Person"}],
                "parts_of_speech": {"normalized": ["noun"]},
                "assignment": {"srs_stage": 0, "started_at": None},
                "review_statistics": {},
            },
            {
                "id": 2,
                "subject_type": "vocabulary",
                "characters": "日本語",
                "readings": [{"reading": "にほんご", "primary": True, "accepted_answer": True}],
                "meanings": [{"meaning": "Japanese Language"}],
                "parts_of_speech": {"normalized": ["noun"]},
                "assignment": {"srs_stage": 0, "started_at": None},
                "review_statistics": {},
            },
            {
                "id": 3,
                "subject_type": "kana_vocabulary",
                "characters": "こんにちは",
                "readings": [],
                "meanings": [{"meaning": "Hello"}],
                "parts_of_speech": {"normalized": ["expression"]},
                "assignment": {"srs_stage": 0, "started_at": None},
                "review_statistics": {},
            },
        ]
    })

    profile = ProfileBuilder(tmp_path).build()
    by_word = {item.word: item for item in profile.vocabulary}

    assert by_word["日本人"].writable is True
    assert by_word["日本語"].writable is False
    assert by_word["こんにちは"].writable is False


def test_writable_tag_is_serialized_only_when_present(tmp_path: Path) -> None:
    _write(tmp_path / "writable_kanji.json", {
        "writable_kanji": [{"character": "猫", "example_words": ["猫"]}]
    })
    _write(tmp_path / "wanikani_index.json", {
        "subjects": [{
            "id": 1,
            "subject_type": "vocabulary",
            "characters": "猫",
            "readings": [{"reading": "ねこ", "primary": True, "accepted_answer": True}],
            "meanings": [{"meaning": "Cat"}],
            "parts_of_speech": {"normalized": ["noun"]},
            "assignment": {"srs_stage": 0, "started_at": None},
            "review_statistics": {},
        }]
    })

    builder = ProfileBuilder(tmp_path)
    builder.build_and_write()
    written = json.loads(builder.output_path.read_text(encoding="utf-8"))
    assert written["vocabulary"][0]["writable"] is True
