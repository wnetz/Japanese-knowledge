from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


HISTORY_SCHEMA_VERSION = 4
SCHEDULE_SCHEMA_VERSION = 1

PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SCHEDULE_PATH = PROJECT_DIR / "output" / "manual" / "daily_goal_schedule.json"


def _write_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def load_goal_schedule(path: Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_SCHEDULE_PATH
    if not path.exists():
        raise FileNotFoundError(f"Daily goal schedule not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Daily goal schedule root must be an object.")

    versions = data.get("versions")
    if not isinstance(versions, list) or not versions:
        raise ValueError("Daily goal schedule must contain at least one version.")

    return data


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def schedule_version_for_date(
    schedule: dict[str, Any],
    target_date: date,
) -> dict[str, Any]:
    """Return the schedule version applicable on target_date.

    Versions are date-ranged. When effective_to is omitted/null, that version
    continues until another version takes over. If several versions overlap,
    the one with the latest effective_from wins.
    """
    candidates: list[tuple[date, dict[str, Any]]] = []

    for version in schedule.get("versions") or []:
        if not isinstance(version, dict):
            continue

        start = _parse_date(version.get("effective_from"))
        end = _parse_date(version.get("effective_to"))
        if start is None:
            continue

        if start <= target_date and (end is None or target_date <= end):
            candidates.append((start, version))

    if candidates:
        candidates.sort(key=lambda item: item[0])
        return candidates[-1][1]

    # For dates before the earliest configured version, use the earliest
    # version rather than making the calendar unusable. Users can add an older
    # version later if they want historically different goals.
    dated_versions = [
        (_parse_date(version.get("effective_from")), version)
        for version in (schedule.get("versions") or [])
        if isinstance(version, dict)
    ]
    dated_versions = [
        (start, version)
        for start, version in dated_versions
        if start is not None
    ]
    if not dated_versions:
        raise ValueError("No valid effective_from dates in daily goal schedule.")

    dated_versions.sort(key=lambda item: item[0])
    return dated_versions[0][1]


def _schedule_day(
    schedule: dict[str, Any],
    target_date: date,
) -> dict[str, Any]:
    version = schedule_version_for_date(schedule, target_date)
    weekly = version.get("weekly_schedule") or {}
    weekday = target_date.strftime("%A").lower()
    day = weekly.get(weekday)
    if not isinstance(day, dict):
        raise ValueError(
            f"Schedule version {version.get('id')!r} has no {weekday} goals."
        )

    parent_goals = version.get("goals") or {}
    resolved_goals: list[dict[str, Any]] = []

    for reference in day.get("goals") or []:
        if not isinstance(reference, dict):
            continue

        goal_id = str(reference.get("id") or "").strip()
        if not goal_id:
            continue

        definition = parent_goals.get(goal_id)

        # Current schema: weekday rows only reference the parent goal id and
        # optional estimated_time.
        if isinstance(definition, dict):
            goal = {
                "id": goal_id,
                **deepcopy(definition),
            }
            estimated_time = str(
                reference.get("estimated_time") or ""
            ).strip()
            if estimated_time:
                goal["estimated_time"] = estimated_time
            resolved_goals.append(goal)
            continue

        # Compatibility for v1 schedule files where each day embedded the
        # entire goal definition.
        goal = deepcopy(reference)
        if "estimated_time" not in goal and goal.get("target"):
            goal["estimated_time"] = str(goal.get("target"))
        resolved_goals.append(goal)

    return {
        "weekday": weekday,
        "schedule_version": str(version.get("id") or ""),
        "approx": str(day.get("approx") or ""),
        "goals": resolved_goals,
    }


# Compatibility views for code/tests that inspect the currently active plan.
# They are derived from the external file; tracker logic itself always reloads
# the schedule file by date.
_current_schedule = load_goal_schedule()
_current_version = schedule_version_for_date(_current_schedule, date.today())
DEFAULT_WEEKLY_SCHEDULE = deepcopy(_current_version.get("weekly_schedule") or {})
ACTIVITY_DEFINITIONS = deepcopy(_current_version.get("goals") or {})



def empty_goal_data(*, start_date: date | None = None) -> dict[str, Any]:
    start_date = start_date or date.today()
    return {
        "schema_version": HISTORY_SCHEMA_VERSION,
        "tracking_started": start_date.isoformat(),
        "records": {},
    }


def _legacy_completed_ids(
    old_completed: set[str],
    target_date: date,
) -> set[str]:
    """Map v1 tracker ids into the revised activity ids."""
    weekday = target_date.strftime("%A").lower()
    mapped: set[str] = set()

    if "reading" in old_completed:
        mapped.add("input_reading")
    if "listening" in old_completed:
        mapped.add("input_listening")
    if "production" in old_completed:
        if weekday == "sunday":
            mapped.add("blind_cumulative_check")
        else:
            mapped.add("typed_production")
    if "grammar" in old_completed:
        if weekday in {"monday", "wednesday", "saturday"}:
            mapped.add("textbook_new_grammar")
        elif weekday == "friday":
            mapped.add("targeted_grammar_repair")
        elif weekday == "sunday":
            mapped.add("blind_cumulative_check")

    # Already-modern ids pass through.
    mapped.update(
        value
        for value in old_completed
        if value
        not in {"reading", "listening", "production", "grammar"}
    )
    return mapped


def _snapshot_record_if_needed(
    record: dict[str, Any],
    target_date: date,
    schedule: dict[str, Any],
) -> bool:
    """Add a schedule snapshot to an older record without one."""
    if isinstance(record.get("goals_snapshot"), list):
        return False

    selected = _schedule_day(schedule, target_date)
    record["schedule_version"] = selected["schedule_version"]
    record["approx_snapshot"] = selected["approx"]
    record["goals_snapshot"] = selected["goals"]
    return True


def load_goal_data(
    path: Path,
    *,
    schedule_path: Path | None = None,
) -> dict[str, Any]:
    schedule = load_goal_schedule(schedule_path)

    if not path.exists():
        return empty_goal_data()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_goal_data()

    if not isinstance(data, dict):
        return empty_goal_data()

    data.setdefault("tracking_started", date.today().isoformat())
    records = data.setdefault("records", {})

    old_version = int(data.get("schema_version") or 1)

    for date_key, record in list(records.items()):
        if not isinstance(record, dict):
            continue

        target_date = _parse_date(date_key)
        if target_date is None:
            continue

        completed = {str(value) for value in (record.get("completed") or [])}
        if old_version < 3:
            completed = _legacy_completed_ids(completed, target_date)
            record["completed"] = sorted(completed)

        _snapshot_record_if_needed(record, target_date, schedule)

    data["schema_version"] = HISTORY_SCHEMA_VERSION

    # v1-v3 embedded the current schedule inside history. It is deliberately
    # removed now: the schedule lives in daily_goal_schedule.json and each
    # recorded day carries its own immutable snapshot.
    data.pop("schedule", None)

    return data


def ensure_goal_file(
    path: Path,
    *,
    start_date: date | None = None,
    schedule_path: Path | None = None,
) -> dict[str, Any]:
    if path.exists():
        data = load_goal_data(path, schedule_path=schedule_path)
        # Persist migrations/snapshots immediately.
        _write_atomic(path, data)
        return data

    data = empty_goal_data(start_date=start_date)
    _write_atomic(path, data)
    return data


def goals_for_date(
    data: dict[str, Any],
    target_date: date,
    *,
    schedule_path: Path | None = None,
) -> dict[str, Any]:
    record = (data.get("records") or {}).get(target_date.isoformat()) or {}

    # Once a day is recorded, its goal definition is frozen in history.
    if isinstance(record.get("goals_snapshot"), list):
        return {
            "weekday": target_date.strftime("%A").lower(),
            "schedule_version": str(record.get("schedule_version") or ""),
            "approx": str(record.get("approx_snapshot") or ""),
            "goals": deepcopy(record["goals_snapshot"]),
        }

    schedule = load_goal_schedule(schedule_path)
    return _schedule_day(schedule, target_date)


def required_goal_ids(
    data: dict[str, Any],
    target_date: date,
    *,
    schedule_path: Path | None = None,
) -> set[str]:
    return {
        str(goal.get("id"))
        for goal in goals_for_date(
            data,
            target_date,
            schedule_path=schedule_path,
        )["goals"]
        if goal.get("id")
    }


def completed_goal_ids(
    data: dict[str, Any],
    target_date: date,
) -> set[str]:
    record = (data.get("records") or {}).get(target_date.isoformat()) or {}
    return {str(value) for value in (record.get("completed") or [])}


def completion_ratio(
    data: dict[str, Any],
    target_date: date,
    *,
    schedule_path: Path | None = None,
) -> float:
    required = required_goal_ids(
        data,
        target_date,
        schedule_path=schedule_path,
    )
    if not required:
        return 0.0

    completed = completed_goal_ids(data, target_date)
    return len(required.intersection(completed)) / len(required)


def day_status(
    data: dict[str, Any],
    target_date: date,
    *,
    today: date | None = None,
    schedule_path: Path | None = None,
) -> str:
    today = today or date.today()

    if target_date > today:
        return "future"

    required = required_goal_ids(
        data,
        target_date,
        schedule_path=schedule_path,
    )
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
    schedule_path: Path | None = None,
) -> dict[str, Any]:
    data = ensure_goal_file(
        path,
        schedule_path=schedule_path,
    )

    existing = (data.get("records") or {}).get(target_date.isoformat()) or {}

    # Existing records keep their original snapshot. A first-time save freezes
    # the schedule version and full goal definitions that were active that day.
    if isinstance(existing.get("goals_snapshot"), list):
        selected = {
            "schedule_version": str(existing.get("schedule_version") or ""),
            "approx": str(existing.get("approx_snapshot") or ""),
            "goals": deepcopy(existing["goals_snapshot"]),
        }
    else:
        schedule = load_goal_schedule(schedule_path)
        selected = _schedule_day(schedule, target_date)

    required = {
        str(goal.get("id"))
        for goal in selected["goals"]
        if goal.get("id")
    }
    valid_completed = sorted(
        {str(value) for value in completed if str(value) in required}
    )

    now = now or datetime.now().astimezone()
    records = data.setdefault("records", {})
    records[target_date.isoformat()] = {
        "completed": valid_completed,
        "notes": str(notes or "").strip(),
        "updated_at": now.isoformat(),
        "schedule_version": selected["schedule_version"],
        "approx_snapshot": selected["approx"],
        "goals_snapshot": deepcopy(selected["goals"]),
    }

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
    schedule_path: Path | None = None,
) -> tuple[int, int]:
    today = today or date.today()
    records = data.get("records") or {}

    if not records:
        return 0, 0

    parsed_dates: list[date] = []
    for key in records:
        parsed = _parse_date(key)
        if parsed is not None:
            parsed_dates.append(parsed)

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
        if day_status(
            data,
            cursor,
            today=today,
            schedule_path=schedule_path,
        ) == "complete":
            run += 1
            longest = max(longest, run)
        else:
            run = 0
        cursor += timedelta(days=1)

    end = today
    if day_status(
        data,
        today,
        today=today,
        schedule_path=schedule_path,
    ) != "complete":
        end = today - timedelta(days=1)

    current = 0
    cursor = end
    while cursor >= started:
        if day_status(
            data,
            cursor,
            today=today,
            schedule_path=schedule_path,
        ) != "complete":
            break
        current += 1
        cursor -= timedelta(days=1)

    return current, longest
