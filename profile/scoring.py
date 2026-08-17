from __future__ import annotations

import math

from core.models import AnkiStudy, MigakuStudy, Vocabulary, WaniKaniStudy


WANIKANI_WEIGHT = 0.70
ANKI_WEIGHT = 0.40
MIGAKU_WEIGHT = 0.20

MIGAKU_KNOWN_SCORE = 0.60
MIGAKU_LEARNING_SCORE = 0.30

WANIKANI_ENLIGHTENED_FLOOR = 0.85
WANIKANI_BURNED_FLOOR = 0.95

ANKI_INTERVAL_FLOORS = (
    (365, 0.95),
    (120, 0.85),
    (60, 0.75),
    (30, 0.65),
    (14, 0.55),
)

# WaniKani stages: 0 locked/unstarted, 1-4 apprentice, 5-6 guru,
# 7 master, 8 enlightened, 9 burned.
_WK_STAGE_SCORES = {
    1: 0.12,
    2: 0.20,
    3: 0.30,
    4: 0.42,
    5: 0.58,
    6: 0.70,
    7: 0.82,
    8: 0.92,
    9: 1.00,
}


def score_wanikani(study: WaniKaniStudy) -> float | None:
    if not study.studied:
        return None

    stage_score = _WK_STAGE_SCORES.get(study.srs_stage or 0, 0.08)
    if study.percentage_correct is None:
        accuracy_score = stage_score
    else:
        accuracy_score = max(0.0, min(1.0, study.percentage_correct / 100.0))

    # SRS stage is the strongest signal; accuracy fine-tunes it.
    return round(max(0.0, min(1.0, stage_score * 0.80 + accuracy_score * 0.20)), 4)


def score_anki(study: AnkiStudy) -> float | None:
    if not study.studied:
        return None

    reviews = max(0, study.reviews)
    interval = max(0, study.best_interval)
    lapses = max(0, study.lapses)

    # Saturating curves prevent huge review counts or intervals from dominating.
    review_score = 1.0 - math.exp(-reviews / 12.0)
    interval_score = 1.0 - math.exp(-interval / 90.0)

    ease = study.ease if study.ease is not None else 2.5
    ease_score = max(0.0, min(1.0, (ease - 1.3) / 1.7))

    lapse_rate = lapses / max(1, reviews)
    lapse_penalty = min(0.45, lapse_rate * 1.8)

    raw = review_score * 0.35 + interval_score * 0.50 + ease_score * 0.15
    return round(max(0.0, min(1.0, raw - lapse_penalty)), 4)


def score_migaku(study: MigakuStudy) -> float | None:
    status = study.status.upper()
    if status == "KNOWN":
        return MIGAKU_KNOWN_SCORE
    if status == "LEARNING":
        return MIGAKU_LEARNING_SCORE
    return None


def calculate_confidence(vocab: Vocabulary) -> float | None:
    contributions: list[tuple[float, float]] = []

    wk = vocab.study.get("wanikani")
    if isinstance(wk, WaniKaniStudy):
        score = score_wanikani(wk)
        if score is not None:
            contributions.append((score, WANIKANI_WEIGHT))

    anki = vocab.study.get("anki")
    if isinstance(anki, AnkiStudy):
        score = score_anki(anki)
        if score is not None:
            contributions.append((score, ANKI_WEIGHT))

    migaku = vocab.study.get("migaku")
    if isinstance(migaku, MigakuStudy):
        score = score_migaku(migaku)
        if score is not None:
            contributions.append((score, MIGAKU_WEIGHT))

    if not contributions:
        return None

    # Weights are renormalized, so an unstudied/missing platform never lowers a score.
    weighted_sum = sum(score * weight for score, weight in contributions)
    total_weight = sum(weight for _, weight in contributions)
    confidence = weighted_sum / total_weight

    # Mature WaniKani states establish a minimum confidence. Other sources can
    # raise confidence, but cannot drag Enlightened/Burned vocabulary below it.
    if isinstance(wk, WaniKaniStudy):
        if wk.srs_stage == 9:
            confidence = max(confidence, WANIKANI_BURNED_FLOOR)
        elif wk.srs_stage == 8:
            confidence = max(confidence, WANIKANI_ENLIGHTENED_FLOOR)

    # Mature Anki intervals establish analogous minimum-confidence floors.
    # Thresholds are checked highest-first so only the strongest applicable
    # floor is used. Other sources may still raise the final confidence.
    if isinstance(anki, AnkiStudy):
        interval = max(0, anki.best_interval)
        for minimum_days, floor in ANKI_INTERVAL_FLOORS:
            if interval >= minimum_days:
                confidence = max(confidence, floor)
                break

    return round(confidence, 4)
