from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .client import BunproClient


class BunproImporter:
    """Build a compact index of the user's Bunpro study knowledge."""

    source_name = "bunpro"

    def __init__(
        self,
        email: str,
        password: str,
        *,
        api_url: str = BunproClient.DEFAULT_API_URL,
        login_url: str = BunproClient.DEFAULT_LOGIN_URL,
        timeout: float = 30.0,
        include_grammar: bool = True,
        include_vocabulary: bool = True,
        client: BunproClient | None = None,
    ) -> None:
        self.client = client or BunproClient(
            email,
            password,
            api_url=api_url,
            login_url=login_url,
            timeout=timeout,
        )
        self.include_grammar = include_grammar
        self.include_vocabulary = include_vocabulary

    def import_data(self) -> dict[str, Any]:
        user = self._normalize_user(self.client.get_user())
        srs_overview = self.client.get_srs_overview()
        jlpt_progress = self.client.get_jlpt_progress()

        grammar = (
            self._collect_reviewables("GrammarPoint")
            if self.include_grammar
            else []
        )
        vocabulary = (
            self._collect_reviewables("Vocab")
            if self.include_vocabulary
            else []
        )

        return {
            "schema_version": 1,
            "source": "bunpro",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "api": "unofficial_frontend",
            "user": user,
            "counts": {
                "grammar": len(grammar),
                "vocabulary": len(vocabulary),
            },
            "srs_overview": srs_overview,
            "jlpt_progress": jlpt_progress,
            "grammar": grammar,
            "vocabulary": vocabulary,
        }

    def _collect_reviewables(self, reviewable_type: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for srs_level in self.client.SRS_LEVELS:
            page = 1
            while True:
                payload = self.client.get_srs_level_details(
                    srs_level,
                    reviewable_type,
                    page=page,
                )
                items.extend(self._normalize_page(payload, srs_level))
                pagy = payload.get("pagy") or {}
                next_page = pagy.get("next")
                if not isinstance(next_page, int) or next_page <= page:
                    break
                page = next_page

        # Defensive de-duplication in case Bunpro returns an item in more than one
        # page/stage during a changing review session.
        deduped: dict[int | str, dict[str, Any]] = {}
        for item in items:
            key = item.get("id")
            if key is not None:
                deduped[key] = item
        return sorted(
            deduped.values(),
            key=lambda item: (
                _jlpt_sort_key(item.get("level")),
                str(item.get("title") or item.get("slug") or ""),
                str(item.get("id") or ""),
            ),
        )

    @staticmethod
    def _normalize_page(payload: dict[str, Any], srs_level: str) -> list[dict[str, Any]]:
        reviews_wrapper = payload.get("reviews") or {}
        reviews = reviews_wrapper.get("data") or []
        included = reviews_wrapper.get("included") or []

        metadata_by_id: dict[str, dict[str, Any]] = {}
        for resource in included:
            if not isinstance(resource, dict):
                continue
            attrs = resource.get("attributes") or {}
            resource_id = attrs.get("id", resource.get("id"))
            if resource_id is not None:
                metadata_by_id[str(resource_id)] = attrs

        normalized: list[dict[str, Any]] = []
        for resource in reviews:
            if not isinstance(resource, dict):
                continue
            review = resource.get("attributes") or {}
            reviewable_id = review.get("reviewable_id")
            meta = metadata_by_id.get(str(reviewable_id), {})
            item = {
                "id": reviewable_id,
                "slug": meta.get("slug"),
                "title": meta.get("title"),
                "meaning": meta.get("meaning"),
                "level": meta.get("level"),
                "study": {
                    "srs_level": srs_level,
                    "streak": review.get("streak"),
                    "accuracy": review.get("accuracy"),
                    "times_studied": review.get("times_studied"),
                    "next_review": review.get("next_review"),
                    "complete": review.get("complete"),
                    "started_studying_at": review.get("started_studying_at"),
                    "ghost_count": review.get("ghost_count"),
                },
            }
            normalized.append(_remove_empty(item))
        return normalized

    @staticmethod
    def _normalize_user(payload: dict[str, Any]) -> dict[str, Any]:
        user_wrapper = payload.get("user") or {}
        data = user_wrapper.get("data") or {}
        attrs = data.get("attributes") or {}
        return _remove_empty({
            "id": attrs.get("id", data.get("id")),
            "username": attrs.get("username"),
            "level": attrs.get("level"),
            "xp": attrs.get("xp"),
            "language": attrs.get("language"),
            "vacation_mode": attrs.get("vacation_mode"),
            "created_at": attrs.get("created_at"),
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


def _jlpt_sort_key(level: Any) -> int:
    text = str(level or "").upper()
    if text.startswith("N") and text[1:].isdigit():
        return 6 - int(text[1:])
    return 99
