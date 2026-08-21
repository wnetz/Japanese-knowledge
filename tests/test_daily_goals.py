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
    assert DEFAULT_WEEKLY_SCHEDULE["monday"]["goals"][0]["target"] == "New material"
    assert DEFAULT_WEEKLY_SCHEDULE["tuesday"]["goals"] == [
        {"id": "reading", "label": "Reading", "target": "10m"},
        {"id": "listening", "label": "Listening", "target": "15–20m"},
    ]
    assert DEFAULT_WEEKLY_SCHEDULE["friday"]["goals"][3]["target"] == "Random review with me"
    assert DEFAULT_WEEKLY_SCHEDULE["saturday"]["goals"][0]["target"] == "New material + cumulative review"
    assert DEFAULT_WEEKLY_SCHEDULE["sunday"]["goals"][3]["target"] == "Weekly test/review"


def test_complete_and_partial_status(tmp_path: Path) -> None:
    path = tmp_path / "daily_goals.json"
    target = date(2026, 8, 21)
    data = empty_goal_data(start_date=target)
    path.write_text(json.dumps(data), encoding="utf-8")

    save_day_record(
        path,
        target,
        {"grammar", "reading"},
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
