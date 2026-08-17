from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import unicodedata


@dataclass(slots=True)
class AnkiStudy:
    reviews: int = 0
    best_interval: int = 0
    lapses: int = 0
    ease: float | None = None
    last_reviewed: str | None = None
    state: str | None = None
    decks: list[str] = field(default_factory=list)

    @property
    def studied(self) -> bool:
        return self.reviews > 0 or self.best_interval > 0 or (
            self.state is not None and self.state.lower() not in {"new", "unknown"}
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviews": self.reviews,
            "ease": self.ease,
            "interval": self.best_interval,
            "last_reviewed": self.last_reviewed,
        }



@dataclass(slots=True)
class WaniKaniStudy:
    srs_stage: int | None = None
    unlocked_at: str | None = None
    started_at: str | None = None
    passed_at: str | None = None
    burned_at: str | None = None
    percentage_correct: int | None = None
    meaning_correct: int = 0
    meaning_incorrect: int = 0
    reading_correct: int = 0
    reading_incorrect: int = 0

    @property
    def studied(self) -> bool:
        return self.started_at is not None or (
            self.srs_stage is not None and self.srs_stage > 0
        ) or self.total_answers > 0

    @property
    def total_answers(self) -> int:
        return (
            self.meaning_correct
            + self.meaning_incorrect
            + self.reading_correct
            + self.reading_incorrect
        )

    def to_dict(self) -> dict[str, Any]:
        return {"srs_stage": self.srs_stage}



@dataclass(slots=True)
class MigakuStudy:
    status: str = ""

    @property
    def studied(self) -> bool:
        return self.status.upper() in {"KNOWN", "LEARNING"}

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status}


@dataclass(slots=True)
class Vocabulary:
    word: str
    reading: str = ""
    meanings: set[str] = field(default_factory=set)
    parts_of_speech: set[str] = field(default_factory=set)
    pitch_accents: set[str] = field(default_factory=set)
    frequency: int | None = None
    sources: set[str] = field(default_factory=set)
    writable: bool = False
    study: dict[str, AnkiStudy | WaniKaniStudy | MigakuStudy] = field(default_factory=dict)
    confidence: float | None = None
    source_ids: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def _canonical_reading(value: str) -> str:
        value = unicodedata.normalize("NFKC", value or "")
        chars: list[str] = []
        for char in value:
            code = ord(char)
            if 0x30A1 <= code <= 0x30F6:
                chars.append(chr(code - 0x60))
            else:
                chars.append(char)
        return "".join(chars)

    @property
    def key(self) -> tuple[str, str]:
        return self.word, self._canonical_reading(self.reading)

    def merge_from(self, other: "Vocabulary") -> None:
        self.meanings.update(other.meanings)
        self.parts_of_speech.update(other.parts_of_speech)
        self.pitch_accents.update(other.pitch_accents)
        self.sources.update(other.sources)
        self.writable = self.writable or other.writable
        self.source_ids.update(other.source_ids)
        self.study.update(other.study)
        if self.frequency is None:
            self.frequency = other.frequency
        elif other.frequency is not None:
            self.frequency = min(self.frequency, other.frequency)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "word": self.word,
            "reading": self.reading,
            "meanings": sorted(self.meanings, key=str.casefold),
            "parts_of_speech": sorted(self.parts_of_speech, key=str.casefold),
            "sources": sorted(self.sources),
            "confidence": self.confidence,
        }
        result["writable"] = self.writable
        if self.study:
            result["study"] = {
                name: data.to_dict() for name, data in sorted(self.study.items())
            }
        return result


@dataclass(slots=True)
class ProfileMetadata:
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sources: list[str] = field(default_factory=list)
    vocabulary_count: int = 0
    confidence_scored_count: int = 0
    unresolved_reading_count: int = 0
    source_counts: dict[str, int] = field(default_factory=dict)
    duplicates_merged: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "sources": self.sources,
            "vocabulary_count": self.vocabulary_count,
            "confidence_scored_count": self.confidence_scored_count,
            "unresolved_reading_count": self.unresolved_reading_count,
            "source_counts": self.source_counts,
            "duplicates_merged": self.duplicates_merged,
        }


@dataclass(slots=True)
class VocabularyProfile:
    metadata: ProfileMetadata
    vocabulary: list[Vocabulary] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "vocabulary": [item.to_dict() for item in self.vocabulary],
        }
