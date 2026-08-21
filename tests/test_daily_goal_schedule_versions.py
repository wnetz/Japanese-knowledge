import json
from datetime import date, datetime, timezone
from pathlib import Path

from goals.tracker import (
    empty_goal_data,
    goals_for_date,
    load_goal_schedule,
    save_day_record,
    schedule_version_for_date,
)


def write_schedule(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "versions": [
                    {
                        "id": "old",
                        "effective_from": "2026-08-01",
                        "effective_to": None,
                        "goals": {
                            "old_goal": {
                                "display": "Old Goal",
                                "what_to_do": "Old instructions",
                                "main_purpose": "Old purpose",
                            }
                        },
                        "weekly_schedule": {
                            "friday": {
                                "approx": "1h",
                                "goals": [
                                    {"id": "old_goal", "estimated_time": "10m"}
                                ],
                            }
                        },
                    },
                    {
                        "id": "new",
                        "effective_from": "2026-09-01",
                        "effective_to": None,
                        "goals": {
                            "new_goal": {
                                "display": "New Goal",
                                "what_to_do": "New instructions",
                                "main_purpose": "New purpose",
                            }
                        },
                        "weekly_schedule": {
                            "friday": {
                                "approx": "2h",
                                "goals": [
                                    {"id": "new_goal", "estimated_time": "20m"}
                                ],
                            }
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_schedule_version_changes_by_effective_date(tmp_path: Path) -> None:
    schedule_path = tmp_path / "schedule.json"
    write_schedule(schedule_path)
    schedule = load_goal_schedule(schedule_path)

    assert schedule_version_for_date(
        schedule,
        date(2026, 8, 21),
    )["id"] == "old"
    assert schedule_version_for_date(
        schedule,
        date(2026, 9, 4),
    )["id"] == "new"


def test_parent_goal_is_resolved_into_daily_goal(tmp_path: Path) -> None:
    schedule_path = tmp_path / "schedule.json"
    write_schedule(schedule_path)
    data = empty_goal_data(start_date=date(2026, 8, 1))

    selected = goals_for_date(
        data,
        date(2026, 8, 21),
        schedule_path=schedule_path,
    )

    assert selected["goals"] == [
        {
            "id": "old_goal",
            "display": "Old Goal",
            "what_to_do": "Old instructions",
            "main_purpose": "Old purpose",
            "estimated_time": "10m",
        }
    ]


def test_recorded_day_keeps_original_goals_after_schedule_changes(tmp_path: Path) -> None:
    schedule_path = tmp_path / "schedule.json"
    history_path = tmp_path / "history.json"
    write_schedule(schedule_path)

    history_path.write_text(
        json.dumps(empty_goal_data(start_date=date(2026, 8, 21))),
        encoding="utf-8",
    )

    save_day_record(
        history_path,
        date(2026, 8, 21),
        {"old_goal"},
        schedule_path=schedule_path,
        now=datetime(2026, 8, 21, 12, tzinfo=timezone.utc),
    )

    # Change the parent definition retroactively. The recorded day's snapshot
    # must still preserve the definition that existed when it was saved.
    schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    schedule["versions"][0]["goals"]["old_goal"]["display"] = "Changed Later"
    schedule_path.write_text(json.dumps(schedule), encoding="utf-8")

    history = json.loads(history_path.read_text(encoding="utf-8"))
    selected = goals_for_date(
        history,
        date(2026, 8, 21),
        schedule_path=schedule_path,
    )

    assert selected["schedule_version"] == "old"
    assert selected["goals"][0]["display"] == "Old Goal"
    assert selected["goals"][0]["what_to_do"] == "Old instructions"
    assert selected["goals"][0]["estimated_time"] == "10m"


def test_unrecorded_day_uses_version_from_schedule_file(tmp_path: Path) -> None:
    schedule_path = tmp_path / "schedule.json"
    write_schedule(schedule_path)
    data = empty_goal_data(start_date=date(2026, 8, 1))

    selected = goals_for_date(
        data,
        date(2026, 9, 4),
        schedule_path=schedule_path,
    )
    assert selected["schedule_version"] == "new"
    assert selected["goals"][0]["display"] == "New Goal"
    assert selected["goals"][0]["estimated_time"] == "20m"
