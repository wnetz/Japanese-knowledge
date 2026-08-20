from datetime import datetime, timezone

from writing.profile import record_occurrence_result
from writing.srs import RESULT_CLOSE, RESULT_CORRECT


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def test_repeated_kanji_positions_are_stored_separately() -> None:
    profile = {"schema_version": 1, "kanji": {}}

    record_occurrence_result(
        profile,
        character="日",
        word="日曜日",
        reading="にちようび",
        position=0,
        result=RESULT_CORRECT,
        targeted=False,
        update_schedule=False,
        reviewed_at=NOW,
    )
    record_occurrence_result(
        profile,
        character="日",
        word="日曜日",
        reading="にちようび",
        position=2,
        result=RESULT_CLOSE,
        targeted=False,
        update_schedule=False,
        reviewed_at=NOW,
    )

    context = profile["kanji"]["日"]["contexts"]["日曜日|にちようび"]
    assert context["positions"]["0"]["correct"] == 1
    assert context["positions"]["2"]["close"] == 1
    assert context["performance"]["attempts"] == 2
    assert context["performance"]["score"] == 0.75
