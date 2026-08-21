from datetime import date

from goals.tracker import load_goal_schedule, schedule_version_for_date


def test_activity_descriptions_come_from_parent_goals_section() -> None:
    schedule = load_goal_schedule()
    version = schedule_version_for_date(schedule, date(2026, 8, 21))
    goals = version["goals"]

    assert goals["typed_production"] == {
        "display": "Typed Production",
        "what_to_do": "English → Japanese, typed, no grammar hints",
        "main_purpose": "High-volume grammar/vocabulary retrieval",
    }
    assert goals["reading"]["display"] == "Reading"
    assert goals["reading"]["main_purpose"] == "Comprehension/automaticity"
    assert goals["listening"]["display"] == "Listening"
