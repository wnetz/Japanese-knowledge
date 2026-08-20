from datetime import datetime, timedelta, timezone

from writing.srs import (
    RESULT_CLOSE,
    RESULT_CORRECT,
    RESULT_FORGOT,
    RESULT_WELL_KNOWN,
    apply_result,
)


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def test_target_correct_advances() -> None:
    result = apply_result(
        {"stage": 3, "graduated_at": NOW.isoformat(), "due": NOW.isoformat()},
        RESULT_CORRECT,
        targeted=True,
        now=NOW,
    )
    assert result["stage"] == 4
    assert datetime.fromisoformat(result["due"]) == NOW + timedelta(days=7)


def test_incidental_correct_does_not_advance_or_move_due() -> None:
    original_due = NOW + timedelta(days=20)
    result = apply_result(
        {"stage": 6, "graduated_at": NOW.isoformat(), "due": original_due.isoformat()},
        RESULT_CORRECT,
        targeted=False,
        now=NOW,
    )
    assert result["stage"] == 6
    assert result["due"] == original_due.isoformat()


def test_incidental_close_regresses_and_pulls_due_earlier() -> None:
    result = apply_result(
        {"stage": 6, "graduated_at": NOW.isoformat(), "due": (NOW + timedelta(days=20)).isoformat()},
        RESULT_CLOSE,
        targeted=False,
        now=NOW,
    )
    assert result["stage"] == 5
    assert datetime.fromisoformat(result["due"]) == NOW + timedelta(days=14)


def test_incidental_forgot_regresses_more_and_pulls_due_earlier() -> None:
    result = apply_result(
        {"stage": 6, "graduated_at": NOW.isoformat(), "due": (NOW + timedelta(days=20)).isoformat()},
        RESULT_FORGOT,
        targeted=False,
        now=NOW,
    )
    assert result["stage"] == 3
    assert datetime.fromisoformat(result["due"]) == NOW + timedelta(days=3)


def test_target_well_known_advances_two_stages() -> None:
    result = apply_result(
        {"stage": 3, "graduated_at": NOW.isoformat(), "due": NOW.isoformat()},
        RESULT_WELL_KNOWN,
        targeted=True,
        now=NOW,
    )
    assert result["stage"] == 5
    assert datetime.fromisoformat(result["due"]) == NOW + timedelta(days=14)


def test_high_stage_forgot_regresses_without_resetting() -> None:
    result = apply_result(
        {"stage": 8, "graduated_at": NOW.isoformat(), "due": (NOW + timedelta(days=120)).isoformat()},
        RESULT_FORGOT,
        targeted=True,
        now=NOW,
    )
    assert result["stage"] == 5
    assert datetime.fromisoformat(result["due"]) == NOW + timedelta(days=14)
