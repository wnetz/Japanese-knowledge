from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "output"

VOCABULARY_PROFILE_PATH = OUTPUT_DIR / "vocabulary_profile.json"
ANKI_INDEX_PATH = OUTPUT_DIR / "anki_index.json"
WANIKANI_INDEX_PATH = OUTPUT_DIR / "wanikani_index.json"
BUNPRO_PRIMARY_PATH = OUTPUT_DIR / "grammar_profile.json"
BUNPRO_FALLBACK_PATH = OUTPUT_DIR / "bunpro_index.json"
UPDATE_PROFILE_PATH = PROJECT_DIR / "update_profile.py"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def save_json(path: Path, value: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temp.replace(path)


def has_kanji(value: str) -> bool:
    for char in value:
        code = ord(char)
        if (
            0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF
        ):
            return True
    return False


def katakana_to_hiragana(value: str) -> str:
    result = []
    for char in value:
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        else:
            result.append(char)
    return "".join(result)


def parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone()


class JMDictReader:
    def __init__(self) -> None:
        try:
            from jamdict import Jamdict
        except ImportError as exc:
            raise RuntimeError(
                "JMdict support is not installed.\n\n"
                "Run:\n"
                "python -m pip install jamdict jamdict-data"
            ) from exc
        self.jam = Jamdict()

    @staticmethod
    def _reading_from_entry_text(entry: Any, word: str) -> str | None:
        text = str(entry)
        escaped = re.escape(word)

        match = re.search(
            r"\]\s+([ぁ-ゖァ-ヺー]+)\s+\(" + escaped + r"\)\s*:",
            text,
        )
        if match:
            return katakana_to_hiragana(match.group(1))

        match = re.search(r"\]\s+([ぁ-ゖァ-ヺー]+)\s*:", text)
        if match and not has_kanji(word):
            return katakana_to_hiragana(match.group(1))
        return None

    def reading(self, word: str) -> str | None:
        result = self.jam.lookup(word)
        exact: list[str] = []
        fallback: list[str] = []

        for entry in result.entries:
            reading = self._reading_from_entry_text(entry, word)
            if reading:
                if f"({word})" in str(entry):
                    exact.append(reading)
                else:
                    fallback.append(reading)

        if exact:
            return exact[0]
        if fallback:
            return fallback[0]
        return None
