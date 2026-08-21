from __future__ import annotations

from typing import Any


WANIKANI_STAGES = (
    "lesson",
    "apprentice_1",
    "apprentice_2",
    "apprentice_3",
    "apprentice_4",
    "guru_1",
    "guru_2",
    "master",
    "enlightened",
    "burned",
)

ANKI_STATES = (
    "new",
    "learning",
    "relearning",
    "review",
)

BUNPRO_STAGES = (
    "beginner",
    "adept",
    "seasoned",
    "expert",
    "master",
    "ghost",
    "self_study",
)

WRITING_STAGES = (
    "new_active",
    "stage_1",
    "stage_2",
    "stage_3",
    "stage_4",
    "stage_5",
    "stage_6",
    "stage_7",
    "stage_8",
)


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def available_anki_decks(history: dict[str, Any]) -> list[str]:
    decks: set[str] = set()
    for day in (history.get("days") or {}).values():
        if not isinstance(day, dict):
            continue
        anki = ((day.get("sources") or {}).get("anki") or {})
        for deck in (anki.get("decks") or {}):
            decks.add(str(deck))
    return sorted(decks, key=str.casefold)


def wanikani_counts(source: dict[str, Any], selection: str) -> dict[str, int]:
    types = source.get("subject_types") or {}

    if selection != "Total":
        selected = types.get(selection) or {}
        return {stage: _int(selected.get(stage)) for stage in WANIKANI_STAGES}

    return {
        stage: sum(
            _int((levels or {}).get(stage))
            for levels in types.values()
            if isinstance(levels, dict)
        )
        for stage in WANIKANI_STAGES
    }


def anki_counts(source: dict[str, Any], selection: str) -> dict[str, int]:
    decks = source.get("decks") or {}

    if selection != "Total":
        selected = decks.get(selection) or {}
        return {state: _int(selected.get(state)) for state in ANKI_STATES}

    return {
        state: sum(
            _int((states or {}).get(state))
            for states in decks.values()
            if isinstance(states, dict)
        )
        for state in ANKI_STATES
    }


def bunpro_counts(
    source: dict[str, Any],
    selection: str,
    content_type: str = "grammar",
) -> dict[str, int] | None:
    # Current schema: grammar/vocabulary -> JLPT level -> SRS stage.
    levels = source.get("levels")
    if isinstance(levels, dict):
        if content_type == "both":
            selected_types = [
                type_levels
                for key, type_levels in levels.items()
                if key in {"grammar", "vocabulary"} and isinstance(type_levels, dict)
            ]
        else:
            selected = levels.get(content_type) or {}
            selected_types = [selected] if isinstance(selected, dict) else []

        if selection == "Total":
            return {
                stage: sum(
                    _int((stage_counts or {}).get(stage))
                    for type_levels in selected_types
                    for stage_counts in type_levels.values()
                    if isinstance(stage_counts, dict)
                )
                for stage in BUNPRO_STAGES
            }

        return {
            stage: sum(
                _int(((type_levels.get(selection) or {}).get(stage)))
                for type_levels in selected_types
            )
            for stage in BUNPRO_STAGES
        }

    # Legacy schema did not preserve JLPT level. Its total is still valid,
    # but an N1-N5 breakdown cannot be reconstructed honestly.
    types = source.get("types")
    if isinstance(types, dict):
        if selection != "Total":
            return None
        if content_type == "both":
            selected_types = [
                stage_counts
                for key, stage_counts in types.items()
                if key in {"grammar", "vocabulary"} and isinstance(stage_counts, dict)
            ]
        else:
            selected = types.get(content_type) or {}
            selected_types = [selected] if isinstance(selected, dict) else []

        return {
            stage: sum(
                _int(stage_counts.get(stage))
                for stage_counts in selected_types
            )
            for stage in BUNPRO_STAGES
        }

    return {stage: 0 for stage in BUNPRO_STAGES}


def writing_counts(source: dict[str, Any]) -> dict[str, int]:
    levels = source.get("levels") or {}
    return {stage: _int(levels.get(stage)) for stage in WRITING_STAGES}


def build_series(
    history: dict[str, Any],
    source_name: str,
    selection: str = "Total",
    *,
    bunpro_content_type: str = "grammar",
) -> tuple[list[str], dict[str, list[int | None]]]:
    source_name = source_name.lower()
    days = history.get("days") or {}
    dates = sorted(str(date) for date in days)

    if source_name == "wanikani":
        stages = WANIKANI_STAGES
    elif source_name == "anki":
        stages = ANKI_STATES
    elif source_name == "bunpro":
        stages = BUNPRO_STAGES
    elif source_name == "writing":
        stages = WRITING_STAGES
    else:
        raise ValueError(f"Unknown history source: {source_name}")

    series: dict[str, list[int | None]] = {stage: [] for stage in stages}

    for date in dates:
        day = days.get(date) or {}
        source = ((day.get("sources") or {}).get(source_name) or {})

        if source_name == "wanikani":
            counts = wanikani_counts(source, selection)
        elif source_name == "anki":
            counts = anki_counts(source, selection)
        elif source_name == "bunpro":
            counts = bunpro_counts(source, selection, bunpro_content_type)
            if counts is None:
                for stage in stages:
                    series[stage].append(None)
                continue
        else:
            counts = writing_counts(source)

        for stage in stages:
            series[stage].append(_int(counts.get(stage)))

    return dates, series
