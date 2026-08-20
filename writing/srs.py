from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

RESULT_WELL_KNOWN = "well_known"
RESULT_CORRECT = "correct"
RESULT_CLOSE = "close"
RESULT_FORGOT = "forgot"
RESULTS = (RESULT_WELL_KNOWN, RESULT_CORRECT, RESULT_CLOSE, RESULT_FORGOT)

# Stage 0 means new/unreviewed. A correct answer advances to stage 1.
# The intervals intentionally stay more aggressive than recognition SRS.
STAGE_INTERVALS = {
    0: timedelta(0),
    1: timedelta(hours=4),
    2: timedelta(days=1),
    3: timedelta(days=3),
    4: timedelta(days=7),
    5: timedelta(days=14),
    6: timedelta(days=30),
    7: timedelta(days=60),
    8: timedelta(days=120),
}
MAX_STAGE = max(STAGE_INTERVALS)

# Failure results regress relative to the current stage rather than resetting
# the kanji. This matters because one difficult vocabulary/pronunciation should
# not erase established writing knowledge.
CLOSE_STAGE_DROP = 1
FORGOT_STAGE_DROP = 3
WELL_KNOWN_STAGE_ADVANCE = 2


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc(value: Any) -> datetime | None:
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
    return parsed.astimezone(timezone.utc)


def new_srs() -> dict[str, Any]:
    return {
        "stage": 0,
        "due": None,
        "introduced_at": None,
        "graduated_at": None,
        "last_reviewed": None,
        "last_result": None,
    }


def is_due(srs: dict[str, Any] | None, now: datetime | None = None) -> bool:
    now = now or utc_now()
    if not isinstance(srs, dict):
        return True
    due = parse_utc(srs.get("due"))
    return due is None or due <= now


def due_at(srs: dict[str, Any] | None) -> datetime | None:
    if not isinstance(srs, dict):
        return None
    return parse_utc(srs.get("due"))


def _earlier_due(
    existing: datetime | None,
    proposed: datetime,
) -> datetime:
    if existing is None:
        return proposed
    return min(existing, proposed)


def apply_result(
    srs: dict[str, Any] | None,
    result: str,
    *,
    targeted: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Apply one writing result to a kanji schedule.

    New kanji remain in the New queue until they are successfully written as
    the target. Close/Forgot keep them at stage 0 with due=None so they can be
    shuffled back into practice immediately.

    Once graduated:
      targeted well_known -> +2 stages
      targeted correct    -> +1 stage
      targeted close      -> -1 stage
      targeted forgot     -> -3 stages

    Incidental positive results never advance an SRS. Incidental failures on a
    graduated kanji can regress it and pull the review earlier.

    Legacy profiles without graduated_at are treated as graduated when stage>0.
    """
    if result not in RESULTS:
        raise ValueError(f"Unknown writing result: {result}")

    now = now or utc_now()
    current = dict(new_srs())
    if isinstance(srs, dict):
        current.update(srs)

    try:
        stage = int(current.get("stage") or 0)
    except (TypeError, ValueError):
        stage = 0
    stage = max(0, min(MAX_STAGE, stage))

    graduated = bool(current.get("graduated_at")) or stage > 0
    existing_due = parse_utc(current.get("due"))

    if graduated and not current.get("graduated_at"):
        current["graduated_at"] = (
            current.get("last_reviewed")
            or current.get("introduced_at")
            or now.isoformat()
        )

    if targeted and not graduated:
        current["introduced_at"] = (
            current.get("introduced_at") or now.isoformat()
        )
        current["last_reviewed"] = now.isoformat()
        current["last_result"] = result

        if result == RESULT_WELL_KNOWN:
            stage = 2
            current["stage"] = stage
            current["graduated_at"] = now.isoformat()
            current["due"] = (now + STAGE_INTERVALS[stage]).isoformat()
            return current

        if result == RESULT_CORRECT:
            stage = 1
            current["stage"] = stage
            current["graduated_at"] = now.isoformat()
            current["due"] = (now + STAGE_INTERVALS[stage]).isoformat()
            return current

        current["stage"] = 0
        current["due"] = None
        return current

    if targeted:
        if result == RESULT_WELL_KNOWN:
            stage = min(MAX_STAGE, stage + WELL_KNOWN_STAGE_ADVANCE)
        elif result == RESULT_CORRECT:
            stage = min(MAX_STAGE, stage + 1)
        elif result == RESULT_CLOSE:
            stage = max(0, stage - CLOSE_STAGE_DROP)
        else:
            stage = max(0, stage - FORGOT_STAGE_DROP)

        current.update(
            {
                "stage": stage,
                "due": (now + STAGE_INTERVALS[stage]).isoformat(),
                "last_reviewed": now.isoformat(),
                "last_result": result,
            }
        )
        return current

    if result in (RESULT_WELL_KNOWN, RESULT_CORRECT):
        return current

    if not graduated:
        current.update(
            {
                "stage": 0,
                "due": None,
                "introduced_at": current.get("introduced_at") or now.isoformat(),
                "last_reviewed": now.isoformat(),
                "last_result": result,
            }
        )
        return current

    if result == RESULT_CLOSE:
        stage = max(0, stage - CLOSE_STAGE_DROP)
    else:
        stage = max(0, stage - FORGOT_STAGE_DROP)

    proposed = now + STAGE_INTERVALS[stage]
    due = _earlier_due(existing_due, proposed)
    current.update(
        {
            "stage": stage,
            "due": due.isoformat(),
            "last_reviewed": now.isoformat(),
            "last_result": result,
        }
    )
    return current


def stage_label(stage: int) -> str:
    if stage <= 0:
        return "New"
    if stage >= MAX_STAGE:
        return f"Stage {MAX_STAGE} · 4 months"
    interval = STAGE_INTERVALS[stage]
    seconds = int(interval.total_seconds())
    if seconds < 86400:
        return f"Stage {stage} · {seconds // 3600}h"
    return f"Stage {stage} · {seconds // 86400}d"
