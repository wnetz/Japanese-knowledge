from core.models import AnkiStudy, Vocabulary
from profile.scoring import calculate_confidence


def test_anki_interval_confidence_floors():
    cases = [
        (119, None),
        (120, 0.75),
        (364, 0.75),
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
            assert confidence < 0.75


def test_anki_interval_floor_table_is_highest_first():
    from profile.scoring import ANKI_INTERVAL_FLOORS

    assert ANKI_INTERVAL_FLOORS == (
        (365, 0.95),
        (120, 0.75),
    )
