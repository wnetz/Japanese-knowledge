from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from core import (
    AnkiStudy,
    MigakuStudy,
    ProfileMetadata,
    Vocabulary,
    VocabularyProfile,
    WaniKaniStudy,
    read_json,
    write_json,
)
from .scoring import calculate_confidence
from .statistics import BuildStatistics


class ProfileBuilder:
    """Build William's vocabulary profile from WaniKani, Anki, and Migaku indexes."""

    SOURCE_FILES = {
        "wanikani": "wanikani_index.json",
        "anki": "anki_index.json",
        "migaku": "migaku_known_words.json",
    }

    def __init__(
        self,
        output_dir: str | Path,
        *,
        output_filename: str = "vocabulary_profile.json",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_path = self.output_dir / output_filename
        self.statistics = BuildStatistics()
        self._items: dict[tuple[str, str], Vocabulary] = {}

    def build(self) -> VocabularyProfile:
        # A builder instance may be reused safely.
        self.statistics = BuildStatistics()
        self._items = {}

        sources = self._load_available_sources()

        for source_name in ("wanikani", "anki", "migaku"):
            data = sources.get(source_name)
            if data is None:
                continue
            entries = list(self._adapt_source(source_name, data))
            self.statistics.source_counts[source_name] = len(entries)
            for entry in entries:
                self._add_or_merge(entry)

        vocabulary = sorted(self._items.values(), key=lambda item: (item.word, item.reading))
        for item in vocabulary:
            item.confidence = calculate_confidence(item)

        self.statistics.vocabulary_count = len(vocabulary)
        self.statistics.confidence_scored_count = sum(
            item.confidence is not None for item in vocabulary
        )
        self.statistics.unresolved_reading_count = sum(
            not item.reading for item in vocabulary
        )

        metadata = ProfileMetadata(
            sources=[name for name in ("wanikani", "anki", "migaku") if name in sources],
            vocabulary_count=self.statistics.vocabulary_count,
            confidence_scored_count=self.statistics.confidence_scored_count,
            unresolved_reading_count=self.statistics.unresolved_reading_count,
            source_counts=dict(self.statistics.source_counts),
            duplicates_merged=self.statistics.duplicates_merged,
        )
        return VocabularyProfile(metadata=metadata, vocabulary=vocabulary)

    def write(self, profile: VocabularyProfile) -> Path:
        return write_json(profile.to_dict(), self.output_path)

    def build_and_write(self) -> VocabularyProfile:
        profile = self.build()
        self.write(profile)
        return profile

    def _load_available_sources(self) -> dict[str, dict[str, Any]]:
        loaded: dict[str, dict[str, Any]] = {}
        for source, filename in self.SOURCE_FILES.items():
            path = self.output_dir / filename
            if not path.exists():
                continue
            data = read_json(path)
            if isinstance(data, dict):
                loaded[source] = data
        return loaded

    def _adapt_source(
        self,
        source_name: str,
        data: dict[str, Any],
    ) -> Iterable[Vocabulary]:
        if source_name == "wanikani":
            return self._adapt_wanikani(data)
        if source_name == "anki":
            return self._adapt_anki(data)
        if source_name == "migaku":
            return self._adapt_migaku(data)
        return []

    def _adapt_wanikani(self, data: dict[str, Any]) -> Iterable[Vocabulary]:
        for subject in data.get("subjects", []):
            if subject.get("subject_type") not in {"vocabulary", "kana_vocabulary"}:
                continue
            word = self._clean(subject.get("characters") or subject.get("slug"))
            if not word:
                continue
            readings = self._wk_readings(subject) or (
                [word] if subject.get("subject_type") == "kana_vocabulary" else [""]
            )
            meanings = {
                self._clean(item.get("meaning"))
                for item in subject.get("meanings", [])
                if self._clean(item.get("meaning"))
            }
            pos = subject.get("parts_of_speech", {})
            if isinstance(pos, dict):
                parts = set(pos.get("normalized") or pos.get("raw") or [])
            else:
                parts = set(pos or [])

            assignment = subject.get("assignment") or {}
            review = subject.get("review_statistics") or {}
            study = WaniKaniStudy(
                srs_stage=assignment.get("srs_stage"),
                unlocked_at=assignment.get("unlocked_at"),
                started_at=assignment.get("started_at"),
                passed_at=assignment.get("passed_at"),
                burned_at=assignment.get("burned_at"),
                percentage_correct=review.get("percentage_correct"),
                meaning_correct=int(review.get("meaning_correct") or 0),
                meaning_incorrect=int(review.get("meaning_incorrect") or 0),
                reading_correct=int(review.get("reading_correct") or 0),
                reading_incorrect=int(review.get("reading_incorrect") or 0),
            )
            for reading in readings:
                yield Vocabulary(
                    word=word,
                    reading=reading,
                    meanings=meanings.copy(),
                    parts_of_speech=parts.copy(),
                    sources={"wanikani"},
                    study={"wanikani": study},
                    source_ids={"wanikani": subject.get("id")},
                )

    def _adapt_anki(self, data: dict[str, Any]) -> Iterable[Vocabulary]:
        for note in data.get("notes", []):
            word = self._clean(note.get("word"))
            reading = self._clean(note.get("reading"))
            if not word:
                continue
            raw_study = note.get("study") or {}
            study = AnkiStudy(
                reviews=int(raw_study.get("reviews") or 0),
                best_interval=int(
                    raw_study.get("best_interval") or raw_study.get("interval") or 0
                ),
                lapses=int(raw_study.get("lapses") or 0),
                ease=(
                    float(raw_study["ease"])
                    if raw_study.get("ease") is not None
                    else None
                ),
                last_reviewed=raw_study.get("last_reviewed"),
                state=raw_study.get("state"),
                decks=list(note.get("decks") or []),
            )
            pitch = self._clean(note.get("pitch_accent"))
            frequency = note.get("frequency")
            try:
                frequency = int(frequency) if frequency not in (None, "") else None
            except (TypeError, ValueError):
                frequency = None
            yield Vocabulary(
                word=word,
                reading=reading,
                meanings={
                    self._clean(value)
                    for value in note.get("meanings", [])
                    if self._clean(value)
                },
                pitch_accents={pitch} if pitch else set(),
                frequency=frequency,
                sources={"anki"},
                study={"anki": study},
            )


    def _adapt_migaku(self, data: dict[str, Any]) -> Iterable[Vocabulary]:
        for item in data.get("words", []):
            if self._clean(item.get("language")).lower() not in {"", "ja", "jpn", "japanese"}:
                continue
            word = self._clean(item.get("word"))
            reading = self._clean(item.get("reading"))
            status = self._clean(item.get("status")).upper()
            if not word or not status:
                continue
            yield Vocabulary(
                word=word,
                reading=reading,
                sources={"migaku"},
                study={"migaku": MigakuStudy(status=status)},
            )

    def _add_or_merge(self, entry: Vocabulary) -> None:
        existing = self._items.get(entry.key)
        if existing is None:
            self._items[entry.key] = entry
            return
        existing.merge_from(entry)
        self.statistics.duplicates_merged += 1

    @staticmethod
    def _wk_readings(subject: dict[str, Any]) -> list[str]:
        readings = subject.get("readings") or []
        accepted = [
            str(item.get("reading", "")).strip()
            for item in readings
            if item.get("accepted_answer", True)
            and str(item.get("reading", "")).strip()
        ]
        primary = [
            str(item.get("reading", "")).strip()
            for item in readings
            if item.get("primary") and str(item.get("reading", "")).strip()
        ]
        return primary or accepted

    @staticmethod
    def _clean(value: Any) -> str:
        return str(value).strip() if value is not None else ""
