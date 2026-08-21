import json
from datetime import date, datetime, timezone
from pathlib import Path

from goals.tracker import (
    DEFAULT_WEEKLY_SCHEDULE,
    day_status,
    empty_goal_data,
    goals_for_date,
    save_day_record,
    streaks,
)


def complete_ids(data, target_date):
    return {
        goal["id"]
        for goal in goals_for_date(data, target_date)["goals"]
    }


def test_schedule_matches_source_file() -> None:
    data = empty_goal_data(start_date=date(2026, 8, 21))

    monday = goals_for_date(data, date(2026, 8, 24))["goals"]
    assert [goal["display"] for goal in monday] == [
        "SRS",
        "Textbook / New Grammar",
        "Typed Production",
        "Reading",
        "Listening",
    ]
    assert monday[2]["estimated_time"] == "20m"
    assert monday[3]["estimated_time"] == "15–20m"
    assert monday[4]["estimated_time"] == "20m"

    friday = goals_for_date(data, date(2026, 8, 21))["goals"]
    assert friday[1]["display"] == "Targeted Grammar Repair"
    assert friday[2]["estimated_time"] == "20–30m"

    sunday = goals_for_date(data, date(2026, 8, 23))["goals"]
    assert [goal["display"] for goal in sunday] == [
        "SRS",
        "Blind Cumulative Check",
        "Reading",
        "Listening",
    ]
    assert sunday[1]["estimated_time"] == "Typed 30–45m + written 15–20m"


def test_complete_and_partial_status(tmp_path: Path) -> None:
    path = tmp_path / "daily_goals.json"
    target = date(2026, 8, 21)
    data = empty_goal_data(start_date=target)
    path.write_text(json.dumps(data), encoding="utf-8")

    save_day_record(
        path,
        target,
        {"targeted_grammar_repair", "reading"},
        now=datetime(2026, 8, 21, 12, tzinfo=timezone.utc),
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert day_status(data, target, today=target) == "partial"

    save_day_record(
        path,
        target,
        complete_ids(data, target),
        now=datetime(2026, 8, 21, 13, tzinfo=timezone.utc),
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert day_status(data, target, today=target) == "complete"


def test_streak_allows_current_day_to_be_unfinished(tmp_path: Path) -> None:
    path = tmp_path / "daily_goals.json"
    start = date(2026, 8, 18)
    today = date(2026, 8, 21)
    path.write_text(json.dumps(empty_goal_data(start_date=start)), encoding="utf-8")

    for target in (date(2026, 8, 18), date(2026, 8, 19), date(2026, 8, 20)):
        data = json.loads(path.read_text(encoding="utf-8"))
        save_day_record(
            path,
            target,
            complete_ids(data, target),
            now=datetime(2026, 8, 21, 12, tzinfo=timezone.utc),
        )

    data = json.loads(path.read_text(encoding="utf-8"))
    assert streaks(data, today=today) == (3, 3)


def test_backfill_earlier_date_updates_tracking_start(tmp_path: Path) -> None:
    path = tmp_path / "daily_goals.json"
    path.write_text(
        json.dumps(empty_goal_data(start_date=date(2026, 8, 21))),
        encoding="utf-8",
    )
    save_day_record(
        path,
        date(2026, 8, 15),
        {"grammar"},
        now=datetime(2026, 8, 21, 12, tzinfo=timezone.utc),
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["tracking_started"] == "2026-08-15"
