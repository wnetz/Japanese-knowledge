from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1

WANIKANI_STAGE_NAMES = {
    0: "lesson",
    1: "apprentice_1",
    2: "apprentice_2",
    3: "apprentice_3",
    4: "apprentice_4",
    5: "guru_1",
    6: "guru_2",
    7: "master",
    8: "enlightened",
    9: "burned",
}

WANIKANI_TYPES = (
    "kana_vocabulary",
    "radical",
    "vocabulary",
    "kanji",
)

BUNPRO_LEVELS = (
    "beginner",
    "adept",
    "seasoned",
    "expert",
    "master",
    "ghost",
    "self_study",
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temp.replace(path)


def _wanikani_snapshot(path: Path) -> dict[str, Any]:
    data = _read_json(path)

    result: dict[str, dict[str, int]] = {
        subject_type: {
            "locked": 0,
            **{name: 0 for name in WANIKANI_STAGE_NAMES.values()},
        }
        for subject_type in WANIKANI_TYPES
    }

    for subject in data.get("subjects", []):
        if not isinstance(subject, dict):
            continue

        subject_type = str(subject.get("subject_type") or "")
        if subject_type not in result:
            continue

        assignment = subject.get("assignment")
        if not isinstance(assignment, dict):
            result[subject_type]["locked"] += 1
            continue

        try:
            stage = int(assignment.get("srs_stage") or 0)
        except (TypeError, ValueError):
            stage = 0

        stage_name = WANIKANI_STAGE_NAMES.get(stage, f"stage_{stage}")
        result[subject_type].setdefault(stage_name, 0)
        result[subject_type][stage_name] += 1

    return {
        "subject_types": result,
        "total": sum(
            sum(levels.values())
            for levels in result.values()
        ),
    }


def _anki_snapshot(path: Path) -> dict[str, Any]:
    data = _read_json(path)

    deck_states: dict[str, Counter[str]] = {}

    for note in data.get("notes", []):
        if not isinstance(note, dict):
            continue

        study = note.get("study") or {}
        if not isinstance(study, dict):
            continue

        state = str(study.get("state") or "unknown").strip().lower()
        if not state:
            state = "unknown"

        decks = note.get("decks") or study.get("decks") or []
        if not isinstance(decks, list):
            decks = []

        normalized_decks = [
            str(deck).strip()
            for deck in decks
            if str(deck).strip()
        ] or ["(unknown)"]

        # A merged note may belong to more than one deck. Count it once in
        # each recorded deck so each deck's SRS distribution stays meaningful.
        for deck in normalized_decks:
            deck_states.setdefault(deck, Counter())[state] += 1

    decks_result: dict[str, dict[str, int]] = {}

    for deck in sorted(deck_states):
        states = deck_states[deck]

        result = {
            "new": states.pop("new", 0),
            "learning": states.pop("learning", 0),
            "relearning": states.pop("relearning", 0),
            "review": states.pop("review", 0),
        }

        for state, count in sorted(states.items()):
            result[state] = count

        decks_result[deck] = result

    return {
        "decks": decks_result,
        "total": sum(
            sum(states.values())
            for states in decks_result.values()
        ),
    }


def _bunpro_snapshot(path: Path) -> dict[str, Any]:
    data = _read_json(path)

    # Bunpro's grammar profile already carries the JLPT level for every
    # grammar/vocabulary item, so preserve that dimension in history instead
    # of collapsing all N5-N1 material together.
    result: dict[str, dict[str, dict[str, int]]] = {}

    for source_key, output_key in (
        ("grammar", "grammar"),
        ("vocabulary", "vocabulary"),
    ):
        by_level: dict[str, Counter[str]] = {}

        for item in data.get(source_key, []):
            if not isinstance(item, dict):
                continue

            raw_level = str(item.get("level") or "unknown").upper()
            if raw_level.startswith("JLPT"):
                level = "N" + raw_level[4:]
            elif raw_level.startswith("N"):
                level = raw_level
            else:
                level = raw_level.lower() or "unknown"

            study = item.get("study") or {}
            if not isinstance(study, dict):
                study = {}

            srs_level = str(study.get("srs_level") or "self_study").strip().lower()
            if not srs_level:
                srs_level = "self_study"

            by_level.setdefault(level, Counter())[srs_level] += 1

        ordered_levels: dict[str, dict[str, int]] = {}
        level_order = ["N5", "N4", "N3", "N2", "N1"]
        extras = sorted(level for level in by_level if level not in level_order)

        for level in level_order + extras:
            if level not in by_level:
                continue
            counts = by_level[level]
            stages = {
                stage: counts.pop(stage, 0)
                for stage in BUNPRO_LEVELS
            }
            for stage, count in sorted(counts.items()):
                stages[stage] = count
            ordered_levels[level] = stages

        result[output_key] = ordered_levels

    return {
        "levels": result,
        "total": sum(
            sum(sum(stages.values()) for stages in levels.values())
            for levels in result.values()
        ),
    }


def _writing_snapshot(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    levels: Counter[str] = Counter()

    for record in (data.get("kanji") or {}).values():
        if not isinstance(record, dict):
            continue

        srs = record.get("srs") or {}
        if not isinstance(srs, dict):
            continue

        try:
            stage = int(srs.get("stage") or 0)
        except (TypeError, ValueError):
            stage = 0

        graduated = bool(srs.get("graduated_at")) or stage > 0
        introduced = bool(srs.get("introduced_at"))

        if not graduated:
            if introduced:
                levels["new_active"] += 1
            else:
                levels["new_unintroduced"] += 1
            continue

        levels[f"stage_{stage}"] += 1

    stable = {
        "new_active": levels.pop("new_active", 0),
        "new_unintroduced": levels.pop("new_unintroduced", 0),
    }
    for stage in range(1, 9):
        stable[f"stage_{stage}"] = levels.pop(f"stage_{stage}", 0)
    for level, count in sorted(levels.items()):
        stable[level] = count

    return {
        "levels": stable,
        "total": sum(stable.values()),
    }


def capture_daily_srs_snapshot(
    *,
    history_path: Path,
    wanikani_path: Path,
    anki_path: Path,
    bunpro_path: Path,
    writing_path: Path,
    now: datetime | None = None,
) -> Path:
    """Create or replace today's SRS snapshot.

    The local calendar date is the key. Repeated runs on the same day replace
    that day's snapshot, so the file can contain at most one entry per day.
    """
    if now is None:
        now = datetime.now().astimezone()
    elif now.tzinfo is None:
        now = now.astimezone()

    # If an aware datetime is supplied, preserve its timezone. The daily key
    # is intentionally based on the caller's local calendar day.
    day_key = now.date().isoformat()

    history = _read_json(history_path)
    if not history:
        history = {
            "schema_version": SCHEMA_VERSION,
            "days": {},
        }

    history["schema_version"] = SCHEMA_VERSION
    days = history.setdefault("days", {})
    if not isinstance(days, dict):
        days = {}
        history["days"] = days

    days[day_key] = {
        "captured_at": now.isoformat(),
        "sources": {
            "wanikani": _wanikani_snapshot(wanikani_path),
            "anki": _anki_snapshot(anki_path),
            "bunpro": _bunpro_snapshot(bunpro_path),
            "writing": _writing_snapshot(writing_path),
        },
    }

    # Keep the file deterministic and chronological.
    history["days"] = {
        key: days[key]
        for key in sorted(days)
    }

    _write_json_atomic(history_path, history)
    return history_path
