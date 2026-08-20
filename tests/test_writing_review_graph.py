from datetime import datetime, timedelta, timezone
from pathlib import Path

from gui import reviews_screen as module


def test_review_screen_source_code_includes_writing() -> None:
    source = Path("gui/reviews_screen.py").read_text(encoding="utf-8")
    assert 'text="Writing"' in source
    assert '"Writing": COLORS["writing"]' in source
    assert 'selected.append("Writing")' in source


def test_writing_loader_uses_scheduled_graduated_items(tmp_path, monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    path = tmp_path / "writing_profile.json"
    path.write_text(
        """{
  "schema_version": 1,
  "kanji": {
    "日": {
      "srs": {
        "stage": 2,
        "graduated_at": "2026-08-20T00:00:00+00:00",
        "due": "%s"
      }
    },
    "月": {
      "srs": {
        "stage": 0,
        "graduated_at": null,
        "due": null
      }
    }
  }
}
""" % ((now + timedelta(hours=4)).isoformat()),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "WRITING_PROFILE_PATH", path)

    # Avoid constructing Tk: loader doesn't depend on widget state.
    screen = object.__new__(module.ReviewsScreen)
    result = screen._load_writing_reviews()

    assert len(result) == 1
    assert result[0]["source"] == "Writing"
    assert result[0]["precision"] == "hour"
