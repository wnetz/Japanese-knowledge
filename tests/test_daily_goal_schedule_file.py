import json
from pathlib import Path


def test_daily_goal_schedule_has_parent_goals_and_compact_days() -> None:
    path = Path("output/manual/daily_goal_schedule.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["schema_version"] == 1
    version = data["versions"][0]
    assert version["effective_from"] == "2026-08-21"

    parent = version["goals"]
    assert parent["typed_production"] == {
        "display": "Typed Production",
        "what_to_do": "English → Japanese, typed, no grammar hints",
        "main_purpose": "High-volume grammar/vocabulary retrieval",
    }
    assert parent["reading"]["display"] == "Reading"
    assert parent["listening"]["display"] == "Listening"

    monday = version["weekly_schedule"]["monday"]["goals"]
    assert monday == [
        {"id": "srs"},
        {"id": "textbook_new_grammar", "estimated_time": "30m"},
        {"id": "typed_production", "estimated_time": "20m"},
        {"id": "reading", "estimated_time": "20m"},
        {"id": "listening", "estimated_time": "20m"},
    ]

    # Day references should not duplicate the parent definition.
    assert all("what_to_do" not in goal for goal in monday)
    assert all("main_purpose" not in goal for goal in monday)
    assert all("display" not in goal for goal in monday)


def test_history_file_no_longer_owns_schedule_definition() -> None:
    history = json.loads(
        Path("output/manual/daily_goals.json").read_text(encoding="utf-8")
    )
    assert "records" in history
    assert "schedule" not in history
