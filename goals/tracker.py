from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1

DEFAULT_WEEKLY_SCHEDULE: dict[str, dict[str, Any]] = {
    "monday": {
        "approx": "1½–2h",
        "goals": [
            {"id": "grammar", "label": "Grammar / Textbook", "target": "New material"},
            {"id": "reading", "label": "Reading", "target": "15–20m"},
            {"id": "listening", "label": "Listening", "target": "20m"},
            {"id": "production", "label": "Production / Writing", "target": "10m"},
        ],
    },
    "tuesday": {
        "approx": "45–60m",
        "goals": [
            {"id": "reading", "label": "Reading", "target": "10m"},
            {"id": "listening", "label": "Listening", "target": "15–20m"},
        ],
    },
    "wednesday": {
        "approx": "1½–2h",
        "goals": [
            {"id": "grammar", "label": "Grammar / Textbook", "target": "New material"},
            {"id": "reading", "label": "Reading", "target": "20m"},
            {"id": "listening", "label": "Listening", "target": "20m"},
            {"id": "production", "label": "Production / Writing", "target": "10–15m"},
        ],
    },
    "thursday": {
        "approx": "45–60m",
        "goals": [
            {"id": "reading", "label": "Reading", "target": "10m"},
            {"id": "listening", "label": "Listening", "target": "15–20m"},
        ],
    },
    "friday": {
        "approx": "1½–2h",
        "goals": [
            {"id": "grammar", "label": "Grammar / Textbook", "target": "Review / weak grammar"},
            {"id": "reading", "label": "Reading", "target": "20–30m"},
            {"id": "listening", "label": "Listening", "target": "20m"},
            {"id": "production", "label": "Production / Writing", "target": "Random review with me"},
        ],
    },
    "saturday": {
        "approx": "2½–3h",
        "goals": [
            {"id": "grammar", "label": "Grammar / Textbook", "target": "New material + cumulative review"},
            {"id": "reading", "label": "Reading", "target": "45–60m"},
            {"id": "listening", "label": "Listening", "target": "30–45m"},
            {"id": "production", "label": "Production / Writing", "target": "20m"},
        ],
    },
    "sunday": {
        "approx": "2–3h",
        "goals": [
            {"id": "grammar", "label": "Grammar / Textbook", "target": "Weekly consolidation"},
            {"id": "reading", "label": "Reading", "target": "45–60m"},
            {"id": "listening", "label": "Listening", "target": "30–45m"},
            {"id": "production", "label": "Production / Writing", "target": "Weekly test/review"},
        ],
    },
}


def _write_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def empty_goal_data(*, start_date: date | None = None) -> dict[str, Any]:
    start_date = start_date or date.today()
    return {
        "schema_version": SCHEMA_VERSION,
        "tracking_started": start_date.isoformat(),
        "schedule": DEFAULT_WEEKLY_SCHEDULE,
        "records": {},
    }


def load_goal_data(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_goal_data()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_goal_data()

    if not isinstance(data, dict):
        return empty_goal_data()

    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("tracking_started", date.today().isoformat())
    data.setdefault("schedule", DEFAULT_WEEKLY_SCHEDULE)
    data.setdefault("records", {})
    return data


def ensure_goal_file(path: Path, *, start_date: date | None = None) -> dict[str, Any]:
    if path.exists():
        return load_goal_data(path)

    data = empty_goal_data(start_date=start_date)
    _write_atomic(path, data)
    return data


def goals_for_date(data: dict[str, Any], target_date: date) -> dict[str, Any]:
    weekday = target_date.strftime("%A").lower()
    schedule = data.get("schedule") or DEFAULT_WEEKLY_SCHEDULE
    day = schedule.get(weekday) or DEFAULT_WEEKLY_SCHEDULE[weekday]
    return {
        "weekday": weekday,
        "approx": str(day.get("approx") or ""),
        "goals": list(day.get("goals") or []),
    }


def required_goal_ids(data: dict[str, Any], target_date: date) -> set[str]:
    return {
        str(goal.get("id"))
        for goal in goals_for_date(data, target_date)["goals"]
        if goal.get("id")
    }


def completed_goal_ids(data: dict[str, Any], target_date: date) -> set[str]:
    record = (data.get("records") or {}).get(target_date.isoformat()) or {}
    return {str(value) for value in (record.get("completed") or [])}


def completion_ratio(data: dict[str, Any], target_date: date) -> float:
    """Return the fraction of scheduled goals completed for a date."""
    required = required_goal_ids(data, target_date)
    if not required:
        return 0.0
    completed = completed_goal_ids(data, target_date)
    return len(required.intersection(completed)) / len(required)



def day_status(
    data: dict[str, Any],
    target_date: date,
    *,
    today: date | None = None,
) -> str:
    today = today or date.today()

    if target_date > today:
        return "future"

    required = required_goal_ids(data, target_date)
    completed = completed_goal_ids(data, target_date)
    records = data.get("records") or {}

    if required and required.issubset(completed):
        return "complete"

    if target_date.isoformat() in records:
        return "partial" if completed else "missed"

    try:
        started = date.fromisoformat(str(data.get("tracking_started")))
    except ValueError:
        started = today

    if target_date < started:
        return "untracked"

    # The current day is still in progress.
    if target_date == today:
        return "untracked"

    return "missed"


def save_day_record(
    path: Path,
    target_date: date,
    completed: set[str] | list[str],
    *,
    notes: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    data = ensure_goal_file(path)

    required = required_goal_ids(data, target_date)
    valid_completed = sorted(
        {str(value) for value in completed if str(value) in required}
    )

    now = now or datetime.now().astimezone()
    records = data.setdefault("records", {})
    records[target_date.isoformat()] = {
        "completed": valid_completed,
        "notes": str(notes or "").strip(),
        "updated_at": now.isoformat(),
    }

    # Backfilled dates become part of the tracked period.
    try:
        started = date.fromisoformat(str(data.get("tracking_started")))
    except ValueError:
        started = target_date
    if target_date < started:
        data["tracking_started"] = target_date.isoformat()

    _write_atomic(path, data)
    return data


def streaks(
    data: dict[str, Any],
    *,
    today: date | None = None,
) -> tuple[int, int]:
    today = today or date.today()
    records = data.get("records") or {}

    if not records:
        return 0, 0

    parsed_dates: list[date] = []
    for key in records:
        try:
            parsed_dates.append(date.fromisoformat(str(key)))
        except ValueError:
            pass

    try:
        started = date.fromisoformat(str(data.get("tracking_started")))
    except ValueError:
        started = min(parsed_dates, default=today)

    if parsed_dates:
        started = min(started, min(parsed_dates))

    longest = 0
    run = 0
    cursor = started
    while cursor <= today:
        if day_status(data, cursor, today=today) == "complete":
            run += 1
            longest = max(longest, run)
        else:
            run = 0
        cursor += timedelta(days=1)

    end = today
    if day_status(data, today, today=today) != "complete":
        end = today - timedelta(days=1)

    current = 0
    cursor = end
    while cursor >= started:
        if day_status(data, cursor, today=today) != "complete":
            break
        current += 1
        cursor -= timedelta(days=1)

    return current, longest
