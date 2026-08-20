from datetime import datetime, timedelta, timezone

from writing.profile import (
    due_counts,
    is_new_kanji,
    record_occurrence_result,
)
from writing.srs import RESULT_CLOSE, RESULT_CORRECT


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def test_incidental_correct_does_not_introduce_new_kanji() -> None:
    profile = {"schema_version": 1, "kanji": {}}

    record_occurrence_result(
        profile,
        character="日",
        word="日曜日",
        reading="にちようび",
        position=0,
        result=RESULT_CORRECT,
        targeted=False,
        update_schedule=True,
        reviewed_at=NOW,
    )

    assert is_new_kanji(profile, "日") is True
    assert profile["kanji"]["日"]["srs"]["due"] is None
    assert profile["kanji"]["日"]["srs"]["introduced_at"] is None


def test_incidental_correct_does_not_instantly_add_to_reviews() -> None:
    profile = {"schema_version": 1, "kanji": {}}

    record_occurrence_result(
        profile,
        character="日",
        word="日曜日",
        reading="にちようび",
        position=0,
        result=RESULT_CORRECT,
        targeted=False,
        update_schedule=True,
        reviewed_at=NOW,
    )

    contexts = {
        "日": [{"word": "日", "reading": "ひ"}],
    }

    new_due, reviews_due = due_counts(
        profile,
        contexts,
        daily_new_limit=10,
        now=NOW,
    )

    assert new_due == 1
    assert reviews_due == 0


def test_incidental_failure_does_introduce_and_schedule_kanji() -> None:
    profile = {"schema_version": 1, "kanji": {}}

    record_occurrence_result(
        profile,
        character="日",
        word="日曜日",
        reading="にちようび",
        position=0,
        result=RESULT_CLOSE,
        targeted=False,
        update_schedule=True,
        reviewed_at=NOW,
    )

    assert is_new_kanji(profile, "日") is True
    assert profile["kanji"]["日"]["srs"]["introduced_at"] == NOW.isoformat()
    assert profile["kanji"]["日"]["srs"]["due"] is None
