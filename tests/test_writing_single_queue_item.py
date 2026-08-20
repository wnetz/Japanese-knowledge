from datetime import datetime, timezone

from writing.profile import choose_target_kanji, record_occurrence_result
from writing.srs import RESULT_FORGOT


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def test_single_new_item_can_repeat_even_if_it_was_previous() -> None:
    profile = {"schema_version": 1, "kanji": {}}
    contexts = {
        "月": [{"word": "月", "reading": "つき"}],
    }

    target = choose_target_kanji(
        profile,
        contexts,
        daily_new_limit=10,
        previous="月",
        now=NOW,
    )
    assert target == "月"


def test_failed_single_new_item_remains_selectable() -> None:
    profile = {"schema_version": 1, "kanji": {}}

    record_occurrence_result(
        profile,
        character="月",
        word="月",
        reading="つき",
        position=0,
        result=RESULT_FORGOT,
        targeted=True,
        reviewed_at=NOW,
    )

    contexts = {
        "月": [{"word": "月", "reading": "つき"}],
    }

    target = choose_target_kanji(
        profile,
        contexts,
        daily_new_limit=10,
        previous="月",
        now=NOW,
    )
    assert target == "月"
