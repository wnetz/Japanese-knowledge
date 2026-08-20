from datetime import datetime, timedelta, timezone

from writing.profile import (
    choose_target_kanji,
    due_counts,
    record_occurrence_result,
)
from writing.srs import RESULT_CORRECT


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def test_daily_new_limit_caps_new_due() -> None:
    profile = {"schema_version": 1, "kanji": {}}
    characters = ["一","二","三","四","五","六","七","八","九","十",
                  "百","千","万","円","年","時","分","半","上","下"]
    contexts = {
        ch: [{"word": ch, "reading": "test"}]
        for ch in characters
    }

    new_due, ongoing_due = due_counts(
        profile,
        contexts,
        daily_new_limit=10,
        now=NOW,
    )

    assert new_due == 10
    assert ongoing_due == 0


def test_new_and_ongoing_share_the_same_random_pool(monkeypatch) -> None:
    profile = {"schema_version": 1, "kanji": {}}

    record_occurrence_result(
        profile,
        character="日",
        word="日本",
        reading="にほん",
        position=0,
        result=RESULT_CORRECT,
        targeted=True,
        reviewed_at=NOW - timedelta(days=10),
    )
    profile["kanji"]["日"]["srs"]["due"] = (
        NOW - timedelta(hours=1)
    ).isoformat()

    contexts = {
        "日": [{"word": "日", "reading": "ひ"}],
        "月": [{"word": "月", "reading": "つき"}],
    }

    seen_pool = {}

    def fake_choice(pool):
        seen_pool["pool"] = list(pool)
        return pool[0]

    monkeypatch.setattr("writing.profile.random.choice", fake_choice)

    choose_target_kanji(
        profile,
        contexts,
        daily_new_limit=10,
        now=NOW,
    )

    assert set(seen_pool["pool"]) == {"日", "月"}
