from __future__ import annotations

import html
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any, Iterable

from config.models import AnkiConfig

from .client import AnkiConnectClient


_SOUND_RE = re.compile(r"\[sound:[^\]]+\]", re.IGNORECASE)
_TAG_BREAK_RE = re.compile(r"<(?:br\s*/?|/p|/div)>", re.IGNORECASE)
_NUMBER_RE = re.compile(r"^[+-]?\d+$")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def get_text(self) -> str:
        return "".join(self.parts)


def _clean_field(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = _SOUND_RE.sub("", text)
    text = _TAG_BREAK_RE.sub("\n", text)
    parser = _TextExtractor()
    try:
        parser.feed(text)
        text = parser.get_text()
    except Exception:
        text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _field_value(card: dict[str, Any], field_name: str) -> str:
    fields = card.get("fields") or {}
    field = fields.get(field_name) if isinstance(fields, dict) else None
    if isinstance(field, dict):
        return _clean_field(field.get("value"))
    return _clean_field(field)


def _parse_frequency(value: str) -> int | str | None:
    cleaned = value.replace(",", "").strip()
    if not cleaned:
        return None
    if _NUMBER_RE.fullmatch(cleaned):
        return int(cleaned)
    return value


def _state_for_card(card: dict[str, Any]) -> str:
    queue = card.get("queue")
    card_type = card.get("type")
    if queue == -1:
        return "suspended"
    if queue in (-2, -3):
        return "buried"
    if card_type == 0:
        return "new"
    if card_type == 1:
        return "learning"
    if card_type == 2:
        return "review"
    if card_type == 3:
        return "relearning"
    return "unknown"


def _positive_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _ease(value: Any) -> float | None:
    try:
        factor = int(value)
    except (TypeError, ValueError):
        return None
    return round(factor / 1000, 3) if factor > 0 else None


def _first_nonempty(values: Iterable[Any]) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _last_reviewed(review_entries: Iterable[Any]) -> str | None:
    latest_ms: int | None = None
    for entry in review_entries:
        value: Any = None
        if isinstance(entry, (list, tuple)) and entry:
            value = entry[0]
        elif isinstance(entry, dict):
            value = entry.get("id") or entry.get("review_time") or entry.get("reviewTime")
        try:
            timestamp_ms = int(value)
        except (TypeError, ValueError):
            continue
        if latest_ms is None or timestamp_ms > latest_ms:
            latest_ms = timestamp_ms
    if latest_ms is None:
        return None
    return datetime.fromtimestamp(latest_ms / 1000, tz=timezone.utc).date().isoformat()


def _exact_due_at(card: dict[str, Any]) -> str | None:
    """Return an exact timestamp for time-scheduled learning/relearning cards."""
    state = _state_for_card(card)
    if state not in {"learning", "relearning"}:
        return None

    try:
        due = int(card.get("due"))
    except (TypeError, ValueError):
        return None

    # Learning/relearning timestamps are Unix seconds. Scheduler-day integers
    # for ordinary review cards are much smaller.
    if due < 1_000_000_000:
        return None

    try:
        return datetime.fromtimestamp(due, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _review_due_date(
    card: dict[str, Any],
    *,
    scheduler_today: int | None,
) -> str | None:
    """Convert Anki's scheduler-day `due` value to a local calendar date."""
    if _state_for_card(card) != "review" or scheduler_today is None:
        return None

    try:
        due_day = int(card.get("due"))
    except (TypeError, ValueError):
        return None

    # A timestamp here would not be a normal scheduler-day review value.
    if due_day >= 1_000_000_000:
        return None

    local_today = datetime.now().astimezone().date()
    offset = due_day - scheduler_today
    return (local_today + timedelta(days=offset)).isoformat()




class AnkiImporter:
    source_name = "anki"

    def __init__(
        self,
        config: AnkiConfig,
        *,
        client: AnkiConnectClient | None = None,
    ) -> None:
        self.config = config
        self.client = client or AnkiConnectClient(
            config.host,
            version=config.api_version,
            timeout_seconds=config.timeout_seconds,
        )

    def _resolve_scheduler_today(self, deck: str) -> int | None:
        """Resolve Anki's internal scheduler-day number using Browser due search.

        `prop:due=N` is relative to Anki's own current review day. Once a
        normal review card with a known offset is found, its raw `due` field
        gives us the scheduler-day origin for converting all review cards.
        """
        escaped_deck = deck.replace('"', '\\"')

        # Prefer current/future cards, then a small overdue window. Usually
        # offset 0 or 1 succeeds immediately.
        offsets = list(range(0, 31)) + list(range(-1, -31, -1))

        for offset in offsets:
            query = (
                f'deck:"{escaped_deck}" '
                f'-is:learn is:review prop:due={offset}'
            )
            card_ids = self.client.find_cards(query)
            if not card_ids:
                continue

            info = self.client.cards_info(card_ids[:1])
            if not info:
                continue

            try:
                raw_due = int(info[0].get("due"))
            except (TypeError, ValueError):
                continue

            if raw_due >= 1_000_000_000:
                continue

            return raw_due - offset

        return None

    def import_data(self) -> dict[str, Any]:
        available_decks = set(self.client.deck_names())
        configured_decks = list(dict.fromkeys(self.config.decks))
        missing_decks = [deck for deck in configured_decks if deck not in available_decks]
        selected_decks = [deck for deck in configured_decks if deck in available_decks]

        errors = [f"Configured Anki deck not found: {deck}" for deck in missing_decks]
        cards: list[dict[str, Any]] = []

        for deck in selected_decks:
            escaped_deck = deck.replace('"', '\\"')
            query = f'deck:"{escaped_deck}"'
            scheduler_today = self._resolve_scheduler_today(deck)
            card_ids = self.client.find_cards(query)
            for batch in _chunks(card_ids, self.config.batch_size):
                batch_cards = self.client.cards_info(batch)
                review_history: dict[str, list[Any]] = {}
                get_reviews = getattr(self.client, "get_reviews_of_cards", None)
                if callable(get_reviews):
                    review_history = get_reviews(batch)
                for card in batch_cards:
                    card_id = card.get("cardId") or card.get("card_id")
                    card["_review_history"] = review_history.get(str(card_id), [])
                    card["_due_date"] = _review_due_date(
                        card,
                        scheduler_today=scheduler_today,
                    )
                    card["_due_at"] = _exact_due_at(card)
                cards.extend(batch_cards)

        entries, conflicts, skipped = self._merge_cards(cards)
        if conflicts:
            errors.extend(
                f"{item['word']}: conflicting {item['field']} values: "
                + " | ".join(item["values"])
                for item in conflicts
            )

        return {
            "schema_version": 1,
            "source": "anki",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "decks": selected_decks,
            "note_count": len(entries),
            "card_count": len(cards),
            "skipped_card_count": skipped,
            "conflict_count": len(conflicts),
            "errors": errors,
            "notes": entries,
        }

    def _merge_cards(
        self,
        cards: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        # Multiple card templates may point at the same Anki note. Collapse those
        # first so a note's fields and deck are not duplicated before word merging.
        by_note: dict[tuple[Any, str], list[dict[str, Any]]] = defaultdict(list)
        for card in cards:
            note_id = card.get("note") or card.get("noteId") or card.get("cardId")
            deck = str(card.get("deckName") or "")
            by_note[(note_id, deck)].append(card)

        normalized_notes: list[dict[str, Any]] = []
        skipped = 0
        for note_cards in by_note.values():
            primary = note_cards[0]
            word = _field_value(primary, self.config.fields.word)
            if not word:
                skipped += len(note_cards)
                continue

            interval_cards = sorted(
                note_cards,
                key=lambda card: _positive_int(card.get("interval")),
                reverse=True,
            )
            best_card = interval_cards[0]
            ease_values = [_ease(card.get("factor")) for card in note_cards]
            normalized_notes.append(
                {
                    "word": word,
                    "reading": _field_value(primary, self.config.fields.reading),
                    "meaning": _field_value(primary, self.config.fields.meaning),
                    "pitch_accent": _field_value(primary, self.config.fields.pitch_accent),
                    "frequency": _parse_frequency(
                        _field_value(primary, self.config.fields.frequency)
                    ),
                    "deck": str(primary.get("deckName") or ""),
                    "study": {
                        "reviews": sum(_positive_int(card.get("reps")) for card in note_cards),
                        "best_interval": max(
                            (_positive_int(card.get("interval")) for card in note_cards),
                            default=0,
                        ),
                        "lapses": sum(_positive_int(card.get("lapses")) for card in note_cards),
                        "ease": max((value for value in ease_values if value is not None), default=None),
                        "last_reviewed": max(
                            (
                                value
                                for value in (
                                    _last_reviewed(card.get("_review_history") or [])
                                    for card in note_cards
                                )
                                if value is not None
                            ),
                            default=None,
                        ),
                        "state": _state_for_card(best_card),
                        "due": best_card.get("due"),
                        "due_date": best_card.get("_due_date"),
                        "due_at": best_card.get("_due_at"),
                        "queue": best_card.get("queue"),
                        "card_type": best_card.get("type"),
                    },
                }
            )

        grouped: dict[tuple[str,str], list[dict[str, Any]]] = defaultdict(list)
        for item in normalized_notes:
            key=(item["word"], (item.get("reading") or "").strip())
            grouped[key].append(item)

        conflicts: list[dict[str, Any]] = []
        merged: list[dict[str, Any]] = []
        for (word, reading), items in grouped.items():
            meaning_values = sorted({str(item["meaning"]) for item in items if item.get("meaning")})
            chosen_meaning = max(meaning_values, key=len) if meaning_values else ""

            study_items = [item["study"] for item in items]
            best_item = max(
                items,
                key=lambda item: item["study"].get("best_interval", 0),
            )
            entry: dict[str, Any] = {
                "word": word,
                "reading": reading,
                "meanings": meaning_values,
                "pitch_accent": _first_nonempty(item.get("pitch_accent") for item in items),
                "frequency": _first_nonempty(item.get("frequency") for item in items),
                "decks": sorted({item["deck"] for item in items if item.get("deck")}),
                "study": {
                    "reviews": sum(item.get("reviews", 0) for item in study_items),
                    "best_interval": max(
                        (item.get("best_interval", 0) for item in study_items),
                        default=0,
                    ),
                    "lapses": sum(item.get("lapses", 0) for item in study_items),
                    "ease": max(
                        (
                            item.get("ease")
                            for item in study_items
                            if item.get("ease") is not None
                        ),
                        default=None,
                    ),
                    "last_reviewed": max(
                        (
                            item.get("last_reviewed")
                            for item in study_items
                            if item.get("last_reviewed")
                        ),
                        default=None,
                    ),
                    "state": best_item["study"].get("state", "unknown"),
                    "due": best_item["study"].get("due"),
                    "due_date": best_item["study"].get("due_date"),
                    "due_at": best_item["study"].get("due_at"),
                    "queue": best_item["study"].get("queue"),
                    "card_type": best_item["study"].get("card_type"),
                },
            }
            merged.append(_remove_empty(entry))

        merged.sort(key=lambda item: item["word"])
        return merged, conflicts, skipped


def _chunks(values: list[int], size: int) -> Iterable[list[int]]:
    size = max(1, size)
    for index in range(0, len(values), size):
        yield values[index:index + size]


def _remove_empty(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {key: _remove_empty(item) for key, item in value.items()}
        return {
            key: item
            for key, item in cleaned.items()
            if item not in (None, "", [], {})
        }
    if isinstance(value, list):
        return [_remove_empty(item) for item in value]
    return value