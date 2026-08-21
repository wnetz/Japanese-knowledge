from history.progress_series import (
    anki_counts,
    available_anki_decks,
    build_series,
    bunpro_counts,
    wanikani_counts,
)


def test_wanikani_total_sums_subject_types_by_stage() -> None:
    source = {
        "subject_types": {
            "radical": {"apprentice_1": 2, "burned": 10},
            "kanji": {"apprentice_1": 3, "burned": 20},
            "vocabulary": {"apprentice_1": 5, "burned": 30},
        }
    }
    result = wanikani_counts(source, "Total")
    assert result["apprentice_1"] == 10
    assert result["burned"] == 60
    assert wanikani_counts(source, "kanji")["burned"] == 20


def test_anki_total_sums_decks_and_lists_all_decks() -> None:
    history = {
        "days": {
            "2026-08-20": {
                "sources": {
                    "anki": {
                        "decks": {
                            "Core": {"new": 10, "review": 5},
                            "Mining": {"new": 3, "review": 7},
                        }
                    }
                }
            },
            "2026-08-21": {
                "sources": {
                    "anki": {
                        "decks": {
                            "Japanese verbs": {"learning": 4},
                        }
                    }
                }
            },
        }
    }
    assert available_anki_decks(history) == [
        "Core",
        "Japanese verbs",
        "Mining",
    ]
    source = history["days"]["2026-08-20"]["sources"]["anki"]
    total = anki_counts(source, "Total")
    assert total["new"] == 13
    assert total["review"] == 12


def test_bunpro_total_and_jlpt_selection_sum_grammar_and_vocabulary() -> None:
    source = {
        "levels": {
            "grammar": {
                "N5": {"beginner": 2, "master": 1},
                "N4": {"beginner": 4},
            },
            "vocabulary": {
                "N5": {"beginner": 3, "master": 8},
                "N4": {"beginner": 6},
            },
        }
    }
    n5 = bunpro_counts(source, "N5", "both")
    assert n5["beginner"] == 5
    assert n5["master"] == 9

    total = bunpro_counts(source, "Total", "both")
    assert total["beginner"] == 15
    assert total["master"] == 9


def test_bunpro_legacy_day_supports_total_but_not_jlpt_breakdown() -> None:
    source = {
        "types": {
            "grammar": {"beginner": 2, "master": 1},
            "vocabulary": {"beginner": 3, "master": 8},
        }
    }
    assert bunpro_counts(source, "Total", "both")["beginner"] == 5
    assert bunpro_counts(source, "N5", "both") is None


def test_build_series_preserves_missing_legacy_bunpro_level_as_none() -> None:
    history = {
        "days": {
            "2026-08-20": {
                "sources": {
                    "bunpro": {
                        "types": {
                            "grammar": {"beginner": 5},
                            "vocabulary": {},
                        }
                    }
                }
            },
            "2026-08-21": {
                "sources": {
                    "bunpro": {
                        "levels": {
                            "grammar": {"N5": {"beginner": 7}},
                            "vocabulary": {"N5": {"beginner": 3}},
                        }
                    }
                }
            },
        }
    }
    dates, series = build_series(history, "bunpro", "N5", bunpro_content_type="both")
    assert dates == ["2026-08-20", "2026-08-21"]
    assert series["beginner"] == [None, 10]


def test_bunpro_content_type_filter_defaults_to_grammar() -> None:
    source = {
        "levels": {
            "grammar": {"N5": {"beginner": 2, "master": 1}},
            "vocabulary": {"N5": {"beginner": 3, "master": 8}},
        }
    }
    assert bunpro_counts(source, "N5")["beginner"] == 2
    assert bunpro_counts(source, "N5", "vocabulary")["master"] == 8
    assert bunpro_counts(source, "N5", "both")["beginner"] == 5
