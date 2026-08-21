from datetime import date

from goals.tracker import empty_goal_data, goals_for_date


def test_embedded_history_schedule_cannot_override_external_schedule() -> None:
    data = empty_goal_data(start_date=date(2026, 8, 21))
    data["schedule"] = {
        "friday": {
            "goals": [{"id": "reading", "estimated_time": "99m"}]
        }
    }

    goals = goals_for_date(data, date(2026, 8, 21))["goals"]
    reading = next(goal for goal in goals if goal["id"] == "reading")
    listening = next(goal for goal in goals if goal["id"] == "listening")

    assert reading["display"] == "Reading"
    assert reading["estimated_time"] == "20–30m"
    assert listening["display"] == "Listening"
    assert listening["estimated_time"] == "20m"
