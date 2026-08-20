from datetime import datetime, timedelta, timezone

from writing.profile import (
    available_due_kanji,
    due_counts,
    is_new_kanji,
    record_occurrence_result,
    valid_contexts_for_target,
)
from writing.srs import RESULT_CORRECT, RESULT_FORGOT

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def graduate(profile, character, word=None, reading="test"):
    word = word or character
    record_occurrence_result(
        profile,
        character=character,
        word=word,
        reading=reading,
        position=word.index(character),
        result=RESULT_CORRECT,
        targeted=True,
        reviewed_at=NOW - timedelta(days=1),
    )


def test_failed_new_target_stays_in_new_pool():
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
    assert is_new_kanji(profile, "月")
    assert profile["kanji"]["月"]["srs"]["due"] is None

    contexts = {"月": [{"word": "月", "reading": "つき"}]}
    new_items, reviews = available_due_kanji(
        profile, contexts, daily_new_limit=10, now=NOW
    )
    assert "月" in new_items
    assert "月" not in reviews


def test_correct_new_target_is_not_review_due_immediately():
    profile = {"schema_version": 1, "kanji": {}}
    record_occurrence_result(
        profile,
        character="月",
        word="月",
        reading="つき",
        position=0,
        result=RESULT_CORRECT,
        targeted=True,
        reviewed_at=NOW,
    )
    contexts = {"月": [{"word": "月", "reading": "つき"}]}
    new_due, reviews_due = due_counts(
        profile, contexts, daily_new_limit=10, now=NOW
    )
    assert new_due == 0
    assert reviews_due == 0
    assert profile["kanji"]["月"]["srs"]["due"] == (
        NOW + timedelta(hours=4)
    ).isoformat()


def test_new_target_rejects_word_with_other_ungraduated_kanji():
    profile = {"schema_version": 1, "kanji": {}}
    contexts = [
        {"word": "月", "reading": "つき"},
        {"word": "月曜日", "reading": "げつようび"},
    ]
    valid = valid_contexts_for_target(profile, "月", contexts)
    assert {item["word"] for item in valid} == {"月"}

    graduate(profile, "曜")
    graduate(profile, "日")
    valid = valid_contexts_for_target(profile, "月", contexts)
    assert {item["word"] for item in valid} == {"月", "月曜日"}


def test_review_target_rejects_word_with_ungraduated_kanji():
    profile = {"schema_version": 1, "kanji": {}}
    graduate(profile, "日")

    contexts = [
        {"word": "日", "reading": "ひ"},
        {"word": "日本", "reading": "にほん"},
    ]
    valid = valid_contexts_for_target(profile, "日", contexts)
    assert {item["word"] for item in valid} == {"日"}

    graduate(profile, "本")
    valid = valid_contexts_for_target(profile, "日", contexts)
    assert {item["word"] for item in valid} == {"日", "日本"}
