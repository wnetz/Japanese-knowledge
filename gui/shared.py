from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "output"
AUTO_OUTPUT_DIR = OUTPUT_DIR / "auto"
MANUAL_OUTPUT_DIR = OUTPUT_DIR / "manual"

VOCABULARY_PROFILE_PATH = AUTO_OUTPUT_DIR / "vocabulary_profile.json"
TEXTBOOK_PROFILE_PATH = AUTO_OUTPUT_DIR / "textbook_profile.json"
GRAMMAR_MASTERY_PATH = MANUAL_OUTPUT_DIR / "grammar_mastery.json"
SRS_HISTORY_PATH = MANUAL_OUTPUT_DIR / "srs_history.json"
DAILY_GOALS_PATH = MANUAL_OUTPUT_DIR / "daily_goals.json"
DAILY_GOAL_SCHEDULE_PATH = MANUAL_OUTPUT_DIR / "daily_goal_schedule.json"
WRITING_PROFILE_PATH = MANUAL_OUTPUT_DIR / "writing_profile.json"
ANKI_INDEX_PATH = AUTO_OUTPUT_DIR / "anki_index.json"
WANIKANI_INDEX_PATH = AUTO_OUTPUT_DIR / "wanikani_index.json"
BUNPRO_PRIMARY_PATH = AUTO_OUTPUT_DIR / "grammar_profile.json"
BUNPRO_FALLBACK_PATH = AUTO_OUTPUT_DIR / "bunpro_index.json"
UPDATE_PROFILE_PATH = PROJECT_DIR / "update_profile.py"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temp.replace(path)


def has_kanji(value: str) -> bool:
    for char in value:
        code = ord(char)
        if (
            0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF
        ):
            return True
    return False


def parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone()
