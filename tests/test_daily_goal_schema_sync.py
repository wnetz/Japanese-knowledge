import json
from pathlib import Path

from goals.tracker import SCHEDULE_SCHEMA_VERSION


def test_schedule_schema_version_is_consistent_everywhere() -> None:
    data = json.loads(
        Path("output/manual/daily_goal_schedule.json").read_text(encoding="utf-8")
    )
    assert SCHEDULE_SCHEMA_VERSION == 1
    assert data["schema_version"] == SCHEDULE_SCHEMA_VERSION
