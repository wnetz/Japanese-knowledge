from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
VALID_MODES = {"production", "recognition"}
VALID_SCORES = {0, 1, 2, 3}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def empty_mastery() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "events": [],
        "items": {},
    }


def load_mastery(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_mastery()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_mastery()
    if not isinstance(data, dict):
        return empty_mastery()
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("events", [])
    data.setdefault("items", {})
    return data


def textbook_items(textbook_profile: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten textbook lesson practice points into selectable grammar items."""
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for lesson in textbook_profile.get("lessons", []):
        if not isinstance(lesson, dict):
            continue
        lesson_id = _clean(lesson.get("id"))
        practice = lesson.get("practice") or {}
        if not isinstance(practice, dict):
            continue

        for kind in ("patterns", "skills"):
            values = practice.get(kind) or []
            if not isinstance(values, list):
                continue
            for value in values:
                text = _clean(value)
                if not text:
                    continue
                key = (lesson_id, kind, text)
                if key in seen:
                    continue
                seen.add(key)
                result.append(
                    {
                        "lesson_id": lesson_id,
                        "kind": kind[:-1] if kind.endswith("s") else kind,
                        "text": text,
                        "item_id": f"{lesson_id}::{text}",
                    }
                )

    return result


def parse_review_results(text: str) -> list[dict[str, Any]]:
    """Parse supported grammar-review result formats.

    Supported formats:

        14-3::たことがあります | production | 3

    and the compact review format used during chat review:

        ～ば                 3  target
        ～たほうがいい       2  incidental
        ～と思います         0  incidental

    Compact rows are production evidence by default. The final target/incidental
    column records whether the grammar point was the intended prompt target.
    """
    observations: list[dict[str, Any]] = []

    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if (
            not line
            or line.startswith("```")
            or line.upper() == "REVIEW RESULTS"
        ):
            continue

        item = ""
        mode = ""
        score: int | None = None
        role = ""

        # Original pipe-separated format.
        parts = [part.strip() for part in line.split("|")]
        if len(parts) == 3:
            item, mode, score_text = parts
            mode = mode.lower()

            try:
                score = int(score_text)
            except ValueError:
                score = None

            if mode not in VALID_MODES:
                continue

        else:
            # Compact format:
            # <grammar item> <0-3> <target|incidental>
            match = re.match(
                r"^(.*?)\s+([0-3])\s+(target|incidental)\s*$",
                line,
                flags=re.IGNORECASE,
            )
            if not match:
                continue

            item = match.group(1).strip()
            score = int(match.group(2))
            role = match.group(3).lower()
            mode = "production"

        if not item or score not in VALID_SCORES:
            continue

        lesson_id = ""
        grammar_text = item
        if "::" in item:
            prefix, remainder = item.split("::", 1)
            if re.fullmatch(r"\d+(?:-\d+)+", prefix):
                lesson_id = prefix
                grammar_text = remainder.strip()

        observations.append(
            {
                "item_id": item,
                "lesson_id": lesson_id,
                "grammar": grammar_text,
                "mode": mode,
                "score": score,
                "role": role,
            }
        )

    return observations


def _summary_for(items: dict[str, Any], observation: dict[str, Any], timestamp: str) -> None:
    item_id = _clean(observation.get("item_id")) or _clean(observation.get("grammar"))
    if not item_id:
        return

    score = int(observation["score"])
    mode = _clean(observation.get("mode")).lower()

    record = items.setdefault(
        item_id,
        {
            "item_id": item_id,
            "lesson_id": _clean(observation.get("lesson_id")),
            "grammar": _clean(observation.get("grammar")) or item_id,
            "attempts": 0,
            "score_sum": 0,
            "average_score": None,
            "last_score": None,
            "last_reviewed": None,
            "modes": {},
        },
    )

    record["attempts"] = int(record.get("attempts") or 0) + 1
    record["score_sum"] = int(record.get("score_sum") or 0) + score
    record["average_score"] = round(
        record["score_sum"] / record["attempts"],
        4,
    )
    record["last_score"] = score
    record["last_reviewed"] = timestamp

    if not record.get("lesson_id"):
        record["lesson_id"] = _clean(observation.get("lesson_id"))
    if not record.get("grammar"):
        record["grammar"] = _clean(observation.get("grammar")) or item_id

    modes = record.setdefault("modes", {})
    mode_record = modes.setdefault(
        mode,
        {
            "attempts": 0,
            "score_sum": 0,
            "average_score": None,
            "last_score": None,
            "last_reviewed": None,
        },
    )
    mode_record["attempts"] = int(mode_record.get("attempts") or 0) + 1
    mode_record["score_sum"] = int(mode_record.get("score_sum") or 0) + score
    mode_record["average_score"] = round(
        mode_record["score_sum"] / mode_record["attempts"],
        4,
    )
    mode_record["last_score"] = score
    mode_record["last_reviewed"] = timestamp


def save_review_event(
    path: Path,
    observations: list[dict[str, Any]],
    *,
    prompt: str = "",
    response: str = "",
    notes: str = "",
    reviewed_at: datetime | None = None,
) -> dict[str, Any]:
    if not observations:
        raise ValueError("A grammar review must contain at least one observation.")

    cleaned: list[dict[str, Any]] = []
    for raw in observations:
        mode = _clean(raw.get("mode")).lower()
        score = int(raw.get("score"))
        grammar = _clean(raw.get("grammar"))
        item_id = _clean(raw.get("item_id")) or grammar

        if not item_id:
            raise ValueError("Every observation needs a grammar item.")
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported review mode: {mode}")
        if score not in VALID_SCORES:
            raise ValueError(f"Score must be 0-3: {score}")

        cleaned.append(
            {
                "item_id": item_id,
                "lesson_id": _clean(raw.get("lesson_id")),
                "grammar": grammar or item_id,
                "mode": mode,
                "score": score,
                "role": _clean(raw.get("role")).lower(),
            }
        )

    reviewed_at = reviewed_at or datetime.now(timezone.utc).astimezone()
    timestamp = reviewed_at.isoformat()

    data = load_mastery(path)
    event = {
        "reviewed_at": timestamp,
        "prompt": _clean(prompt),
        "response": _clean(response),
        "notes": _clean(notes),
        "observations": cleaned,
    }
    data["events"].append(event)

    items = data.setdefault("items", {})
    for observation in cleaned:
        _summary_for(items, observation, timestamp)

    _atomic_write(path, data)
    return event
