from core.models import AnkiStudy, Vocabulary
from profile.scoring import calculate_confidence


def test_anki_interval_confidence_floors():
    cases = [
        (13, None),
        (14, 0.55),
        (30, 0.65),
        (60, 0.75),
        (120, 0.85),
        (365, 0.95),
    ]

    for interval, expected_floor in cases:
        vocab = Vocabulary(
            word=f"interval-{interval}",
            study={
                "anki": AnkiStudy(
                    reviews=1,
                    best_interval=interval,
                    lapses=10,
                    ease=1.3,
                    state="review",
                )
            },
        )
        confidence = calculate_confidence(vocab)
        assert confidence is not None
        if expected_floor is not None:
            assert confidence >= expected_floor
        else:
            assert confidence < 0.55
