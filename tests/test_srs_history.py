import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from history.srs_history import capture_daily_srs_snapshot


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def make_sources(tmp_path: Path):
    wk = tmp_path / "wanikani.json"
    anki = tmp_path / "anki.json"
    bunpro = tmp_path / "bunpro.json"
    writing = tmp_path / "writing.json"

    write(
        wk,
        {
            "subjects": [
                {"subject_type": "kanji", "assignment": {"srs_stage": 1}},
                {"subject_type": "kanji", "assignment": {"srs_stage": 9}},
                {"subject_type": "radical", "assignment": {"srs_stage": 5}},
                {"subject_type": "vocabulary", "assignment": {"srs_stage": 8}},
                {"subject_type": "kana_vocabulary", "assignment": {"srs_stage": 2}},
                {"subject_type": "kanji"},
            ]
        },
    )
    write(
        anki,
        {
            "notes": [
                {"study": {"state": "new"}},
                {"study": {"state": "learning"}},
                {"study": {"state": "review"}},
            ]
        },
    )
    write(
        bunpro,
        {
            "srs_overview": {
                "grammar": {
                    "beginner": 2,
                    "adept": 3,
                    "seasoned": 4,
                    "expert": 5,
                    "master": 6,
                    "ghost": 1,
                    "self_study": 0,
                },
                "vocab": {
                    "beginner": 7,
                    "adept": 8,
                    "seasoned": 9,
                    "expert": 10,
                    "master": 11,
                    "ghost": 0,
                    "self_study": 0,
                },
            }
        },
    )
    write(
        writing,
        {
            "kanji": {
                "日": {
                    "srs": {
                        "stage": 3,
                        "graduated_at": "2026-08-01T00:00:00+00:00",
                    }
                },
                "月": {
                    "srs": {
                        "stage": 0,
                        "introduced_at": "2026-08-20T00:00:00+00:00",
                        "graduated_at": None,
                    }
                },
            }
        },
    )
    return wk, anki, bunpro, writing


def test_wanikani_is_split_by_subject_type_and_stage(tmp_path: Path) -> None:
    wk, anki, bunpro, writing = make_sources(tmp_path)
    history = tmp_path / "manual" / "srs_history.json"

    capture_daily_srs_snapshot(
        history_path=history,
        wanikani_path=wk,
        anki_path=anki,
        bunpro_path=bunpro,
        writing_path=writing,
        now=datetime(2026, 8, 20, 20, 0, tzinfo=timezone.utc),
    )

    data = json.loads(history.read_text(encoding="utf-8"))
    snapshot = data["days"]["2026-08-20"]["sources"]["wanikani"]["subject_types"]

    assert snapshot["kanji"]["apprentice_1"] == 1
    assert snapshot["kanji"]["burned"] == 1
    assert snapshot["kanji"]["locked"] == 1
    assert snapshot["radical"]["guru_1"] == 1
    assert snapshot["vocabulary"]["enlightened"] == 1
    assert snapshot["kana_vocabulary"]["apprentice_2"] == 1


def test_only_one_entry_per_local_day_and_latest_replaces(tmp_path: Path) -> None:
    wk, anki, bunpro, writing = make_sources(tmp_path)
    history = tmp_path / "manual" / "srs_history.json"

    first = datetime(2026, 8, 20, 8, 0, tzinfo=timezone(timedelta(hours=9)))
    second = datetime(2026, 8, 20, 22, 0, tzinfo=timezone(timedelta(hours=9)))

    capture_daily_srs_snapshot(
        history_path=history,
        wanikani_path=wk,
        anki_path=anki,
        bunpro_path=bunpro,
        writing_path=writing,
        now=first,
    )
    capture_daily_srs_snapshot(
        history_path=history,
        wanikani_path=wk,
        anki_path=anki,
        bunpro_path=bunpro,
        writing_path=writing,
        now=second,
    )

    data = json.loads(history.read_text(encoding="utf-8"))
    assert list(data["days"]) == ["2026-08-20"]
    assert data["days"]["2026-08-20"]["captured_at"] == second.isoformat()


def test_native_source_levels_are_recorded(tmp_path: Path) -> None:
    wk, anki, bunpro, writing = make_sources(tmp_path)
    history = tmp_path / "manual" / "srs_history.json"

    capture_daily_srs_snapshot(
        history_path=history,
        wanikani_path=wk,
        anki_path=anki,
        bunpro_path=bunpro,
        writing_path=writing,
        now=datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc),
    )

    sources = json.loads(history.read_text(encoding="utf-8"))["days"]["2026-08-20"]["sources"]

    assert sources["anki"]["states"]["new"] == 1
    assert sources["anki"]["states"]["learning"] == 1
    assert sources["anki"]["states"]["review"] == 1
    assert sources["bunpro"]["types"]["grammar"]["master"] == 6
    assert sources["bunpro"]["types"]["vocabulary"]["master"] == 11
    assert sources["writing"]["levels"]["new_active"] == 1
    assert sources["writing"]["levels"]["stage_3"] == 1
