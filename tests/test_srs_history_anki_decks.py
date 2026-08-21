import json
from datetime import datetime, timezone
from pathlib import Path

from history.srs_history import capture_daily_srs_snapshot


def test_history_keeps_all_anki_decks(tmp_path: Path) -> None:
    wk = tmp_path / "wk.json"
    bp = tmp_path / "bp.json"
    writing = tmp_path / "writing.json"
    anki = tmp_path / "anki.json"
    history = tmp_path / "history.json"

    wk.write_text('{"subjects":[]}', encoding="utf-8")
    bp.write_text('{"srs_overview":{}}', encoding="utf-8")
    writing.write_text('{"kanji":{}}', encoding="utf-8")
    anki.write_text(json.dumps({
        "notes": [
            {"decks":["Core"], "study":{"state":"review"}},
            {"decks":["Mining"], "study":{"state":"new"}},
            {"decks":["Japanese verbs (N5 - N4)"], "study":{"state":"learning"}}
        ]
    }), encoding="utf-8")

    capture_daily_srs_snapshot(
        history_path=history,
        wanikani_path=wk,
        anki_path=anki,
        bunpro_path=bp,
        writing_path=writing,
        now=datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc),
    )

    decks = json.loads(history.read_text(encoding="utf-8"))[
        "days"
    ]["2026-08-20"]["sources"]["anki"]["decks"]

    assert set(decks) == {
        "Core",
        "Mining",
        "Japanese verbs (N5 - N4)",
    }
    assert decks["Japanese verbs (N5 - N4)"]["learning"] == 1
