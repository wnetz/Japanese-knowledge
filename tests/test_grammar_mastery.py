import json
from datetime import datetime, timezone
from pathlib import Path

from grammar.mastery import (
    parse_review_block,
    parse_review_results,
    save_review_event,
    textbook_items,
)


def test_parse_multiple_review_observations() -> None:
    parsed = parse_review_results(
        """
REVIEW RESULTS
14-3::たことがあります | production | 3
particle::に/で | production | 1
adjective::い→く | production | 0
"""
    )
    assert len(parsed) == 3
    assert parsed[0]["lesson_id"] == "14-3"
    assert parsed[0]["grammar"] == "たことがあります"
    assert parsed[1]["item_id"] == "particle::に/で"
    assert parsed[2]["score"] == 0


def test_save_event_updates_each_item_independently(tmp_path: Path) -> None:
    path = tmp_path / "grammar_mastery.json"
    now = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)

    save_review_event(
        path,
        [
            {
                "item_id": "14-3::たことがあります",
                "lesson_id": "14-3",
                "grammar": "たことがあります",
                "mode": "production",
                "score": 3,
            },
            {
                "item_id": "particle::に/で",
                "lesson_id": "",
                "grammar": "particle::に/で",
                "mode": "production",
                "score": 0,
            },
        ],
        reviewed_at=now,
    )

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["events"]) == 1
    assert data["items"]["14-3::たことがあります"]["average_score"] == 3.0
    assert data["items"]["particle::に/で"]["average_score"] == 0.0


def test_textbook_items_include_lesson_patterns() -> None:
    profile = {
        "lessons": [
            {
                "id": "14-3",
                "practice": {
                    "patterns": ["#～ たことがあります"],
                    "skills": ["[[辞書形]]こと"],
                },
            }
        ]
    }
    items = textbook_items(profile)
    assert {item["item_id"] for item in items} == {
        "14-3::#～ たことがあります",
        "14-3::[[辞書形]]こと",
    }


def test_parse_compact_target_incidental_format() -> None:
    parsed = parse_review_results(
        """～ば                 3  target
～たほうがいい       2  incidental
～と思います         0  incidental"""
    )

    assert len(parsed) == 3
    assert parsed[0]["grammar"] == "～ば"
    assert parsed[0]["score"] == 3
    assert parsed[0]["role"] == "target"
    assert parsed[0]["mode"] == "production"

    assert parsed[1]["grammar"] == "～たほうがいい"
    assert parsed[1]["score"] == 2
    assert parsed[1]["role"] == "incidental"

    assert parsed[2]["grammar"] == "～と思います"
    assert parsed[2]["score"] == 0
    assert parsed[2]["role"] == "incidental"


def test_parse_review_block_with_prompt_and_response() -> None:
    parsed = parse_review_block(
        """～たことがあります／ありません    3  incidental
～と思います                      3  target
prompt:\tI think my younger brother has never eaten sushi.
response: 弟が寿司を食べたことがないと思います"""
    )

    assert len(parsed["observations"]) == 2
    assert parsed["observations"][0]["grammar"] == "～たことがあります／ありません"
    assert parsed["observations"][0]["score"] == 3
    assert parsed["observations"][0]["role"] == "incidental"
    assert parsed["observations"][1]["grammar"] == "～と思います"
    assert parsed["observations"][1]["role"] == "target"
    assert parsed["prompt"] == "I think my younger brother has never eaten sushi."
    assert parsed["response"] == "弟が寿司を食べたことがないと思います"


def test_parse_review_block_supports_multiline_context() -> None:
    parsed = parse_review_block(
        """～ば  2 target
prompt: First line
second line
response: 日本語
続き"""
    )

    assert parsed["prompt"] == "First line\nsecond line"
    assert parsed["response"] == "日本語\n続き"
