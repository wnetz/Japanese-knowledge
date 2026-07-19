from __future__ import annotations

import math

from core.models import AnkiStudy, Vocabulary, WaniKaniStudy


WANIKANI_WEIGHT = 0.70
ANKI_WEIGHT = 0.30

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

    if not contributions:
        return None

    # Weights are renormalized, so an unstudied/missing platform never lowers a score.
    weighted_sum = sum(score * weight for score, weight in contributions)
    total_weight = sum(weight for _, weight in contributions)
    return round(weighted_sum / total_weight, 4)
