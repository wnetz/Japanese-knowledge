from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import WaniKaniClient
from .normalization import normalize_parts_of_speech


class WaniKaniImporter:
    source_name = "wanikani"
    """Build a normalized WaniKani index for the Knowledge Engine."""

    DEFAULT_SUBJECT_TYPES = ("radical", "kanji", "vocabulary", "kana_vocabulary")

    def __init__(
        self,
        api_token: str,
        *,
        include_user: bool = True,
        include_subjects: bool = True,
        include_assignments: bool = True,
        include_review_statistics: bool = True,
        include_mnemonics: bool = True,
        include_context_sentences: bool = True,
        subject_types: tuple[str, ...] | list[str] | None = None,
        client: WaniKaniClient | None = None,
    ) -> None:
        self.client = client or WaniKaniClient(api_token)
        self.include_user = include_user
        self.include_subjects = include_subjects
        self.include_assignments = include_assignments
        self.include_review_statistics = include_review_statistics
        self.include_mnemonics = include_mnemonics
        self.include_context_sentences = include_context_sentences
        self.subject_types = tuple(subject_types or self.DEFAULT_SUBJECT_TYPES)

    def import_all(self) -> dict[str, Any]:
        user = self._get_user() if self.include_user else {}
        subjects = (
            list(self.client.iter_collection("subjects", {"types": self.subject_types}))
            if self.include_subjects
            else []
        )

        assignments = self._by_subject_id("assignments") if self.include_assignments else {}
        review_statistics = (
            self._by_subject_id("review_statistics")
            if self.include_review_statistics
            else {}
        )

        normalized = [
            self._normalize_subject(
                subject,
                assignment=assignments.get(subject.get("id")),
                review_statistic=review_statistics.get(subject.get("id")),
            )
            for subject in subjects
        ]

        normalized.sort(key=lambda item: (item.get("level", 999), item["subject_type"], item["id"]))
        counts = Counter(item["subject_type"] for item in normalized)

        return {
            "schema_version": 1,
            "source": "wanikani",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "api_revision": self.client.REVISION,
            "user": user,
            "subject_count": len(normalized),
            "counts_by_type": dict(sorted(counts.items())),
            "includes": {
                "user": self.include_user,
                "subjects": self.include_subjects,
                "assignments": self.include_assignments,
                "review_statistics": self.include_review_statistics,
                "mnemonics": self.include_mnemonics,
                "context_sentences": self.include_context_sentences,
            },
            "subjects": normalized,
        }

    def import_data(self) -> dict[str, Any]:
        return self.import_all()

    def save_json(self, output_path: str | Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.import_all(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

    def _get_user(self) -> dict[str, Any]:
        payload = self.client.get("user")
        data = payload.get("data") or {}
        subscription = data.get("subscription") or {}
        return _remove_empty({
            "username": data.get("username"),
            "level": data.get("level"),
            "profile_url": data.get("profile_url"),
            "started_at": data.get("started_at"),
            "subscription": {
                "active": subscription.get("active"),
                "type": subscription.get("type"),
                "max_level_granted": subscription.get("max_level_granted"),
            },
        })

    def _by_subject_id(self, endpoint: str) -> dict[int, dict[str, Any]]:
        result: dict[int, dict[str, Any]] = {}
        for item in self.client.iter_collection(endpoint):
            data = item.get("data") or {}
            subject_id = data.get("subject_id")
            if isinstance(subject_id, int):
                result[subject_id] = item
        return result

    def _normalize_subject(
        self,
        subject: dict[str, Any],
        *,
        assignment: dict[str, Any] | None,
        review_statistic: dict[str, Any] | None,
    ) -> dict[str, Any]:
        data = subject.get("data") or {}
        subject_type = str(subject.get("object") or "unknown")

        entry: dict[str, Any] = {
            "id": subject.get("id"),
            "subject_type": subject_type,
            "level": data.get("level"),
            "characters": data.get("characters"),
            "slug": data.get("slug"),
            "document_url": data.get("document_url"),
            "created_at": subject.get("data_updated_at"),
            "hidden_at": data.get("hidden_at"),
            "meanings": self._normalize_meanings(data.get("meanings", [])),
            "readings": self._normalize_readings(data.get("readings", [])),
            "component_subject_ids": data.get("component_subject_ids", []),
            "amalgamation_subject_ids": data.get("amalgamation_subject_ids", []),
            "visually_similar_subject_ids": data.get("visually_similar_subject_ids", []),
        }

        pos = data.get("parts_of_speech") or []
        if pos:
            entry["parts_of_speech"] = normalize_parts_of_speech(pos)

        if self.include_mnemonics:
            entry["mnemonics"] = _remove_empty({
                "meaning": data.get("meaning_mnemonic"),
                "meaning_hint": data.get("meaning_hint"),
                "reading": data.get("reading_mnemonic"),
                "reading_hint": data.get("reading_hint"),
            })

        if self.include_context_sentences and data.get("context_sentences"):
            entry["context_sentences"] = [
                _remove_empty({
                    "ja": sentence.get("ja"),
                    "en": sentence.get("en"),
                })
                for sentence in data["context_sentences"]
                if isinstance(sentence, dict)
            ]

        if assignment:
            entry["assignment"] = self._normalize_assignment(assignment)
        if review_statistic:
            entry["review_statistics"] = self._normalize_review_statistic(review_statistic)

        return _remove_empty(entry)

    @staticmethod
    def _normalize_meanings(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            _remove_empty({
                "meaning": item.get("meaning"),
                "primary": item.get("primary"),
                "accepted_answer": item.get("accepted_answer"),
            })
            for item in items
            if isinstance(item, dict)
        ]

    @staticmethod
    def _normalize_readings(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            _remove_empty({
                "reading": item.get("reading"),
                "primary": item.get("primary"),
                "accepted_answer": item.get("accepted_answer"),
                "type": item.get("type"),
            })
            for item in items
            if isinstance(item, dict)
        ]

    @staticmethod
    def _normalize_assignment(item: dict[str, Any]) -> dict[str, Any]:
        data = item.get("data") or {}
        return _remove_empty({
            "id": item.get("id"),
            "srs_stage": data.get("srs_stage"),
            "unlocked_at": data.get("unlocked_at"),
            "started_at": data.get("started_at"),
            "passed_at": data.get("passed_at"),
            "burned_at": data.get("burned_at"),
            "available_at": data.get("available_at"),
            "resurrected_at": data.get("resurrected_at"),
            "hidden": data.get("hidden"),
        })

    @staticmethod
    def _normalize_review_statistic(item: dict[str, Any]) -> dict[str, Any]:
        data = item.get("data") or {}
        return _remove_empty({
            "id": item.get("id"),
            "meaning_correct": data.get("meaning_correct"),
            "meaning_incorrect": data.get("meaning_incorrect"),
            "meaning_max_streak": data.get("meaning_max_streak"),
            "meaning_current_streak": data.get("meaning_current_streak"),
            "reading_correct": data.get("reading_correct"),
            "reading_incorrect": data.get("reading_incorrect"),
            "reading_max_streak": data.get("reading_max_streak"),
            "reading_current_streak": data.get("reading_current_streak"),
            "percentage_correct": data.get("percentage_correct"),
        })


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
