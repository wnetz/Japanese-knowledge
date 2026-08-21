import json
from datetime import date
from pathlib import Path

from goals.tracker import (
    goal_timers,
    save_day_record,
    save_goal_timer,
)


def write_schedule(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "versions": [
                    {
                        "id": "v1",
                        "effective_from": "2026-01-01",
                        "effective_to": None,
                        "goals": {
                            "timed": {
                                "display": "Timed",
                                "what_to_do": "Do it",
                                "main_purpose": "Test",
                            },
                            "untimed": {
                                "display": "Untimed",
                                "what_to_do": "Do it",
                                "main_purpose": "Test",
                            },
                        },
                        "weekly_schedule": {
                            "friday": {
                                "approx": "20m",
                                "goals": [
                                    {"id": "timed", "estimated_time": "20m"},
                                    {"id": "untimed"},
                                ],
                            }
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_timer_is_created_and_persisted_with_day_record(tmp_path: Path) -> None:
    history = tmp_path / "daily_goals.json"
    schedule = tmp_path / "schedule.json"

    write_schedule(schedule)
    data = save_day_record(
        history,
        date(2026, 8, 21),
        set(),
        schedule_path=schedule,
    )

    timers = goal_timers(data, date(2026, 8, 21))
    assert timers["timed"]["initial_seconds"] == 1200
    assert timers["timed"]["remaining_seconds"] == 1200
    assert timers["timed"]["running"] is False
    assert "untimed" not in timers


def test_marking_timed_goal_complete_sets_timer_to_zero(tmp_path: Path) -> None:
    history = tmp_path / "daily_goals.json"
    schedule = tmp_path / "schedule.json"

    write_schedule(schedule)
    save_day_record(history, date(2026, 8, 21), set(), schedule_path=schedule)
    data = save_day_record(
        history,
        date(2026, 8, 21),
        {"timed"},
        schedule_path=schedule,
    )

    timer = goal_timers(data, date(2026, 8, 21))["timed"]
    assert timer["remaining_seconds"] == 0
    assert timer["running"] is False
    assert timer["deadline"] is None


def test_unchecking_completed_timed_goal_resets_timer(tmp_path: Path) -> None:
    history = tmp_path / "daily_goals.json"
    schedule = tmp_path / "schedule.json"

    write_schedule(schedule)
    save_day_record(
        history,
        date(2026, 8, 21),
        {"timed"},
        schedule_path=schedule,
    )
    data = save_day_record(
        history,
        date(2026, 8, 21),
        set(),
        schedule_path=schedule,
    )

    timer = goal_timers(data, date(2026, 8, 21))["timed"]
    assert timer["remaining_seconds"] == 1200
    assert timer["running"] is False
    assert timer["notified"] is False


def test_running_timer_deadline_is_preserved_on_disk(tmp_path: Path) -> None:
    history = tmp_path / "daily_goals.json"
    schedule = tmp_path / "schedule.json"

    write_schedule(schedule)
    save_day_record(history, date(2026, 8, 21), set(), schedule_path=schedule)

    data = save_goal_timer(
        history,
        date(2026, 8, 21),
        "timed",
        {
            "initial_seconds": 1200,
            "remaining_seconds": 900,
            "running": True,
            "deadline": "2026-08-21T12:15:00+09:00",
            "notified": False,
        },
        schedule_path=schedule,
    )

    timer = goal_timers(data, date(2026, 8, 21))["timed"]
    assert timer["running"] is True
    assert timer["remaining_seconds"] == 900
    assert timer["deadline"] == "2026-08-21T12:15:00+09:00"


def test_existing_record_migrates_timer_state(tmp_path: Path) -> None:
    from goals.tracker import ensure_goal_file

    history = tmp_path / "daily_goals.json"
    schedule = tmp_path / "schedule.json"
    write_schedule(schedule)

    history.write_text(
        json.dumps(
            {
                "schema_version": 4,
                "tracking_started": "2026-08-21",
                "records": {
                    "2026-08-21": {
                        "completed": [],
                        "notes": "",
                        "schedule_version": "v1",
                        "approx_snapshot": "20m",
                        "goals_snapshot": [
                            {
                                "id": "timed",
                                "display": "Timed",
                                "estimated_time": "20m",
                            },
                            {
                                "id": "untimed",
                                "display": "Untimed",
                            },
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    data = ensure_goal_file(history, schedule_path=schedule)
    timers = data["records"]["2026-08-21"]["timers"]

    assert timers["timed"]["remaining_seconds"] == 1200
    assert "untimed" not in timers
    assert data["schema_version"] == 5
