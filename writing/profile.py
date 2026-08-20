from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from .srs import (
    RESULT_CLOSE,
    RESULT_CORRECT,
    RESULT_FORGOT,
    RESULT_WELL_KNOWN,
    apply_result,
    due_at,
    is_due,
    new_srs,
    utc_now,
)



def _load_json(path: Path) -> dict[str, Any]:
    import json
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_json(path: Path, data: dict[str, Any]) -> None:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


SCHEMA_VERSION = 1
RESULT_WEIGHT = {
    RESULT_WELL_KNOWN: 1.0,
    RESULT_CORRECT: 1.0,
    RESULT_CLOSE: 0.5,
    RESULT_FORGOT: 0.0,
}


def empty_performance() -> dict[str, Any]:
    return {
        "attempts": 0,
        "well_known": 0,
        "correct": 0,
        "close": 0,
        "forgot": 0,
        "score": None,
        "first_reviewed": None,
        "last_result": None,
        "last_reviewed": None,
    }


def empty_profile() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kanji": {},
    }


def load_writing_profile(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_profile()
    data = _load_json(path)
    if not isinstance(data.get("kanji"), dict):
        data["kanji"] = {}
    data["schema_version"] = SCHEMA_VERSION
    return data


def save_writing_profile(path: Path, profile: dict[str, Any]) -> None:
    profile["schema_version"] = SCHEMA_VERSION
    _save_json(path, profile)


def kanji_occurrences(word: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    for index, char in enumerate(word):
        code = ord(char)
        if (
            0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF
        ):
            result.append((index, char))
    return result


def context_key(word: str, reading: str) -> str:
    return f"{word}|{reading}"


def _kanji_record(profile: dict[str, Any], character: str) -> dict[str, Any]:
    records = profile.setdefault("kanji", {})
    record = records.setdefault(
        character,
        {
            "srs": new_srs(),
            "performance": empty_performance(),
            "contexts": {},
        },
    )
    record.setdefault("srs", new_srs())
    record.setdefault("performance", empty_performance())
    record.setdefault("contexts", {})
    return record


def _update_performance(
    performance: dict[str, Any],
    result: str,
    reviewed_at: datetime,
) -> None:
    attempts = int(performance.get("attempts") or 0) + 1
    performance["attempts"] = attempts
    if attempts == 1 and not performance.get("first_reviewed"):
        performance["first_reviewed"] = reviewed_at.isoformat()
    performance[result] = int(performance.get(result) or 0) + 1

    weighted = (
        int(performance.get("well_known") or 0)
        + int(performance.get("correct") or 0)
        + 0.5 * int(performance.get("close") or 0)
    )
    performance["score"] = round(weighted / attempts, 4)
    performance["last_result"] = result
    performance["last_reviewed"] = reviewed_at.isoformat()


def record_occurrence_result(
    profile: dict[str, Any],
    *,
    character: str,
    word: str,
    reading: str,
    position: int,
    result: str,
    targeted: bool,
    update_schedule: bool = True,
    reviewed_at: datetime | None = None,
) -> None:
    reviewed_at = reviewed_at or utc_now()
    record = _kanji_record(profile, character)

    _update_performance(record["performance"], result, reviewed_at)

    key = context_key(word, reading)
    context = record["contexts"].setdefault(
        key,
        {
            "word": word,
            "reading": reading,
            "performance": empty_performance(),
            "positions": {},
        },
    )
    _update_performance(context["performance"], result, reviewed_at)

    positions = context.setdefault("positions", {})
    position_record = positions.setdefault(str(position), empty_performance())
    _update_performance(position_record, result, reviewed_at)

    if update_schedule:
        record["srs"] = apply_result(
            record.get("srs"),
            result,
            targeted=targeted,
            now=reviewed_at,
        )


def context_performance(
    profile: dict[str, Any],
    character: str,
    word: str,
    reading: str,
) -> dict[str, Any]:
    record = profile.get("kanji", {}).get(character, {})
    context = record.get("contexts", {}).get(context_key(word, reading), {})
    performance = context.get("performance")
    return performance if isinstance(performance, dict) else empty_performance()


def kanji_performance(
    profile: dict[str, Any],
    character: str,
) -> dict[str, Any]:
    record = profile.get("kanji", {}).get(character, {})
    performance = record.get("performance")
    return performance if isinstance(performance, dict) else empty_performance()


def kanji_srs(profile: dict[str, Any], character: str) -> dict[str, Any]:
    record = profile.get("kanji", {}).get(character, {})
    srs = record.get("srs")
    return srs if isinstance(srs, dict) else new_srs()


def is_new_kanji(profile: dict[str, Any], character: str) -> bool:
    srs = kanji_srs(profile, character)
    try:
        stage = int(srs.get("stage") or 0)
    except (TypeError, ValueError):
        stage = 0
    return not bool(srs.get("graduated_at")) and stage <= 0


def is_introduced_kanji(profile: dict[str, Any], character: str) -> bool:
    return bool(kanji_srs(profile, character).get("introduced_at"))


def is_graduated_kanji(profile: dict[str, Any], character: str) -> bool:
    srs = kanji_srs(profile, character)
    try:
        stage = int(srs.get("stage") or 0)
    except (TypeError, ValueError):
        stage = 0
    return bool(srs.get("graduated_at")) or stage > 0


def new_reviews_started_today(
    profile: dict[str, Any],
    *,
    now: datetime | None = None,
) -> int:
    now = now or utc_now()
    today = now.astimezone().date()
    count = 0

    for record in profile.get("kanji", {}).values():
        if not isinstance(record, dict):
            continue

        srs = record.get("srs") or {}
        if not isinstance(srs, dict):
            continue

        introduced_at = srs.get("introduced_at")
        if not introduced_at:
            continue

        try:
            parsed = datetime.fromisoformat(str(introduced_at))
        except ValueError:
            continue

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        if parsed.astimezone().date() == today:
            count += 1

    return count


def valid_contexts_for_target(
    profile: dict[str, Any],
    character: str,
    contexts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Only allow prompts whose other kanji have already been graduated."""
    target_is_new = is_new_kanji(profile, character)
    valid: list[dict[str, Any]] = []

    for item in contexts:
        word = str(item.get("word") or "")
        word_kanji = {char for _, char in kanji_occurrences(word)}
        if character not in word_kanji:
            continue

        if target_is_new:
            others = word_kanji - {character}
            if all(is_graduated_kanji(profile, other) for other in others):
                valid.append(item)
        else:
            if all(is_graduated_kanji(profile, char) for char in word_kanji):
                valid.append(item)

    return valid


def valid_context_map(
    profile: dict[str, Any],
    contexts_by_kanji: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for character, contexts in contexts_by_kanji.items():
        valid = valid_contexts_for_target(profile, character, contexts)
        if valid:
            result[character] = valid
    return result


def due_counts(
    profile: dict[str, Any],
    contexts_by_kanji: dict[str, list[dict[str, Any]]],
    *,
    daily_new_limit: int,
    now: datetime | None = None,
) -> tuple[int, int]:
    now = now or utc_now()
    valid_map = valid_context_map(profile, contexts_by_kanji)

    active_new = [
        char
        for char in valid_map
        if is_new_kanji(profile, char) and is_introduced_kanji(profile, char)
    ]

    started_today = new_reviews_started_today(profile, now=now)
    remaining_slots = max(0, daily_new_limit - started_today)

    fresh_new = [
        char
        for char in valid_map
        if is_new_kanji(profile, char) and not is_introduced_kanji(profile, char)
    ]

    new_due = len(active_new) + min(len(fresh_new), remaining_slots)

    reviews_due = sum(
        1
        for char in valid_map
        if is_graduated_kanji(profile, char)
        and is_due(kanji_srs(profile, char), now)
    )
    return new_due, reviews_due


def available_due_kanji(
    profile: dict[str, Any],
    contexts_by_kanji: dict[str, list[dict[str, Any]]],
    *,
    daily_new_limit: int,
    now: datetime | None = None,
) -> tuple[list[str], list[str]]:
    now = now or utc_now()
    valid_map = valid_context_map(profile, contexts_by_kanji)

    active_new = [
        char
        for char in valid_map
        if is_new_kanji(profile, char) and is_introduced_kanji(profile, char)
    ]

    started_today = new_reviews_started_today(profile, now=now)
    remaining_slots = max(0, daily_new_limit - started_today)

    fresh_new = [
        char
        for char in valid_map
        if is_new_kanji(profile, char) and not is_introduced_kanji(profile, char)
    ]
    random.shuffle(fresh_new)
    fresh_new = fresh_new[:remaining_slots]

    reviews_due = [
        char
        for char in valid_map
        if is_graduated_kanji(profile, char)
        and is_due(kanji_srs(profile, char), now)
    ]
    return active_new + fresh_new, reviews_due


def choose_target_kanji(
    profile: dict[str, Any],
    contexts_by_kanji: dict[str, list[dict[str, Any]]],
    *,
    daily_new_limit: int,
    previous: str | None = None,
    now: datetime | None = None,
) -> str | None:
    new_due, ongoing_due = available_due_kanji(
        profile,
        contexts_by_kanji,
        daily_new_limit=daily_new_limit,
        now=now,
    )

    # New and ongoing reviews deliberately share one random pool so they
    # interleave during practice rather than appearing in separate blocks.
    pool = list(new_due) + list(ongoing_due)

    if not pool:
        return None

    if previous in pool:
        without_previous = [
            char
            for char in pool
            if char != previous
        ]

        # Avoid immediate repeats only when there is a genuine alternative.
        # If this is the sole remaining New/Review item, keep it selectable.
        if without_previous:
            pool = without_previous

    return random.choice(pool)


def choose_context(
    profile: dict[str, Any],
    character: str,
    contexts: list[dict[str, Any]],
    *,
    previous_key: tuple[str, str] | None = None,
) -> dict[str, Any] | None:
    if not contexts:
        return None

    candidates = list(contexts)
    if len(candidates) > 1 and previous_key is not None:
        without_previous = [
            item
            for item in candidates
            if (
                str(item.get("word") or ""),
                str(item.get("reading") or ""),
            ) != previous_key
        ]
        if without_previous:
            candidates = without_previous

    untested = [
        item
        for item in candidates
        if int(
            context_performance(
                profile,
                character,
                str(item.get("word") or ""),
                str(item.get("reading") or ""),
            ).get("attempts")
            or 0
        )
        == 0
    ]
    if untested:
        return random.choice(untested)

    # Weak contexts get more weight, while every context keeps a chance of
    # appearing so the quiz does not become deterministic.
    weights: list[float] = []
    now = utc_now()
    for item in candidates:
        perf = context_performance(
            profile,
            character,
            str(item.get("word") or ""),
            str(item.get("reading") or ""),
        )
        try:
            score = float(perf.get("score"))
        except (TypeError, ValueError):
            score = 0.0

        weakness = 1.0 - max(0.0, min(1.0, score))
        last = perf.get("last_reviewed")
        recency_bonus = 1.0
        if last:
            try:
                parsed = datetime.fromisoformat(str(last))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                age_days = max(0.0, (now - parsed.astimezone(timezone.utc)).total_seconds() / 86400)
                recency_bonus = min(2.0, 0.5 + age_days / 7.0)
            except ValueError:
                pass

        weights.append(0.2 + weakness * 2.0 + recency_bonus)

    return random.choices(candidates, weights=weights, k=1)[0]
