from __future__ import annotations

import json
import re
import unicodedata
from copy import deepcopy
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from core import read_json, write_json


PROFILE_SCHEMA_VERSION = 1
ALIASES_SCHEMA_VERSION = 1
CANDIDATE_SCHEMA_VERSION = 1

ITEM_TYPES = {
    "grammar",
    "conjugation",
    "pattern",
    "skill",
    "particle",
    "observed",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def normalize_surface(value: Any) -> str:
    """Conservative normalization used for exact cross-source matching.

    This intentionally does not remove Japanese grammar markers, polite forms,
    or textbook placeholders because those can change meaning.
    """
    text = unicodedata.normalize("NFKC", _clean(value))
    text = text.replace("〜", "～").replace("~", "～")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _slug(value: str) -> str:
    value = normalize_surface(value)
    return value.replace("::", "：：")


def _typed_id(item_type: str, display: str) -> str:
    item_type = item_type if item_type in ITEM_TYPES else "observed"
    return f"{item_type}::{_slug(display)}"


def _read_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = read_json(path)
    return value if isinstance(value, dict) else {}


def load_aliases(path: Path) -> list[dict[str, str]]:
    data = _read_optional(path)
    aliases = data.get("aliases") or []
    result: list[dict[str, str]] = []
    for entry in aliases:
        if not isinstance(entry, dict):
            continue

        source = _clean(entry.get("source"))
        canonical_id = _clean(entry.get("canonical_id"))

        # Support both the original singular `value` form and the more
        # convenient `values` list form. This keeps existing manual alias files
        # fully backward compatible.
        raw_values: list[Any] = []
        if entry.get("value") is not None:
            raw_values.append(entry.get("value"))

        values = entry.get("values")
        if isinstance(values, list):
            raw_values.extend(values)

        seen_values: set[str] = set()
        for raw_value in raw_values:
            value = normalize_surface(raw_value)
            if not source or not value or not canonical_id:
                continue
            if value in seen_values:
                continue
            seen_values.add(value)

            result.append(
                {
                    "source": source,
                    "value": value,
                    "canonical_id": canonical_id,
                }
            )
    return result


class GrammarProfileBuilder:
    """Merge grammar source indexes and usage evidence into one profile."""

    def __init__(
        self,
        output_dir: str | Path,
        *,
        grammar_index_filename: str = "auto/grammar_index.json",
        textbook_index_filename: str = "auto/textbook_index.json",
        grammar_use_index_filename: str = "manual/grammar_use_index.json",
        aliases_filename: str = "manual/grammar_aliases.json",
        alias_candidates_filename: str = "auto/grammar_alias_candidates.json",
        output_filename: str = "auto/grammar_profile.json",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.grammar_index_path = self.output_dir / grammar_index_filename
        self.textbook_index_path = self.output_dir / textbook_index_filename
        self.grammar_use_index_path = self.output_dir / grammar_use_index_filename
        self.aliases_path = self.output_dir / aliases_filename
        self.alias_candidates_path = self.output_dir / alias_candidates_filename
        self.output_path = self.output_dir / output_filename

        self.items: dict[str, dict[str, Any]] = {}
        self.alias_lookup: dict[tuple[str, str], str] = {}
        self.representations: list[dict[str, str]] = []
        self.source_counts: dict[str, int] = {}

    def build(self) -> dict[str, Any]:
        self.items = {}
        self.representations = []
        self.source_counts = {}

        aliases = load_aliases(self.aliases_path)
        self.alias_lookup = {
            (entry["source"], entry["value"]): entry["canonical_id"]
            for entry in aliases
        }

        grammar_index = _read_optional(self.grammar_index_path)
        textbook_index = _read_optional(self.textbook_index_path)
        grammar_use_index = _read_optional(self.grammar_use_index_path)

        self._add_bunpro(grammar_index)
        self._add_textbook(textbook_index)
        self._add_use(grammar_use_index)

        candidates = self._build_alias_candidates()
        write_json(
            {
                "schema_version": CANDIDATE_SCHEMA_VERSION,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "candidates": candidates,
            },
            self.alias_candidates_path,
        )

        return {
            "schema_version": PROFILE_SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_files": {
                "grammar_index": str(self.grammar_index_path),
                "textbook_index": str(self.textbook_index_path),
                "grammar_use_index": str(self.grammar_use_index_path),
                "grammar_aliases": str(self.aliases_path),
            },
            "source_counts": dict(self.source_counts),
            "item_count": len(self.items),
            "items": dict(sorted(self.items.items())),
        }

    def write(self, profile: dict[str, Any]) -> Path:
        return write_json(profile, self.output_path)

    def build_and_write(self) -> dict[str, Any]:
        profile = self.build()
        self.write(profile)
        return profile

    def _canonical_id(
        self,
        *,
        source: str,
        value: str,
        item_type: str,
    ) -> str:
        normalized = normalize_surface(value)
        alias = self.alias_lookup.get((source, normalized))
        if alias:
            return alias

        # Exact normalized display matches are safe to merge.
        for item_id, item in self.items.items():
            if (
                normalize_surface(item.get("display")) == normalized
                and item.get("type") == item_type
            ):
                return item_id

        return _typed_id(item_type, normalized)

    def _ensure_item(
        self,
        item_id: str,
        *,
        item_type: str,
        display: str,
    ) -> dict[str, Any]:
        item = self.items.get(item_id)
        if item is None:
            item = {
                "item_id": item_id,
                "type": item_type,
                "display": normalize_surface(display),
                "aliases": {},
                "sources": {},
                "lessons": [],
                "use": None,
            }
            self.items[item_id] = item
        return item

    def _remember_representation(
        self,
        *,
        source: str,
        value: str,
        canonical_id: str,
        item_type: str,
    ) -> None:
        normalized = normalize_surface(value)
        if not normalized:
            return
        self.representations.append(
            {
                "source": source,
                "value": normalized,
                "canonical_id": canonical_id,
                "type": item_type,
            }
        )
        item = self.items[canonical_id]
        aliases = item.setdefault("aliases", {})
        values = aliases.setdefault(source, [])
        if normalized not in values:
            values.append(normalized)

    def _add_bunpro(self, data: dict[str, Any]) -> None:
        count = 0
        for raw in data.get("grammar") or []:
            if not isinstance(raw, dict):
                continue
            display = normalize_surface(raw.get("title") or raw.get("slug"))
            if not display:
                continue

            item_id = self._canonical_id(
                source="bunpro",
                value=display,
                item_type="grammar",
            )
            item = self._ensure_item(
                item_id,
                item_type="grammar",
                display=display,
            )
            item["sources"]["bunpro"] = deepcopy(raw)
            self._remember_representation(
                source="bunpro",
                value=display,
                canonical_id=item_id,
                item_type="grammar",
            )
            count += 1

        self.source_counts["grammar_index"] = count

    @staticmethod
    def _skill_reference_names(value: Any) -> list[str]:
        """Return textbook wiki-link names referenced by a skill string."""
        text = _clean(value)
        names = []
        for match in re.finditer(r"\[\[([^\]#]+)(?:#[^\]]+)?\]\]", text):
            name = normalize_surface(match.group(1))
            if name:
                names.append(name)
        return names

    @staticmethod
    def _conjugation_reference_name(value: str) -> str:
        """Normalize a textbook conjugation skill reference to its form name."""
        name = normalize_surface(value)
        if name.endswith("動詞"):
            name = name[:-2]
        return name

    def _conjugation_lessons(
        self,
        textbook_data: dict[str, Any],
    ) -> dict[str, list[str]]:
        """Map top-level conjugation form names to lessons that reference them."""
        mapping: dict[str, list[str]] = {}

        for lesson in textbook_data.get("lessons") or []:
            if not isinstance(lesson, dict):
                continue
            lesson_id = _clean(lesson.get("id"))
            practice = lesson.get("practice") or {}
            if not isinstance(practice, dict):
                continue

            for skill in practice.get("skills") or []:
                for reference in self._skill_reference_names(skill):
                    form_name = self._conjugation_reference_name(reference)
                    if not form_name:
                        continue
                    lessons = mapping.setdefault(form_name, [])
                    if lesson_id and lesson_id not in lessons:
                        lessons.append(lesson_id)

        return mapping

    def _add_textbook(self, data: dict[str, Any]) -> None:
        count = 0
        conjugation_lessons = self._conjugation_lessons(data)

        # Conjugation entries are top-level curriculum items.
        conjugation_seen: dict[str, int] = {}
        for raw in data.get("conjugations") or []:
            if not isinstance(raw, dict):
                continue
            display = normalize_surface(raw.get("name"))
            if not display:
                continue

            conjugation_seen[display] = conjugation_seen.get(display, 0) + 1
            occurrence = conjugation_seen[display]

            item_id = self._canonical_id(
                source="textbook",
                value=display,
                item_type="conjugation",
            )
            # Preserve distinct duplicate source entries instead of silently
            # collapsing conflicting conjugation definitions.
            if occurrence > 1 and item_id in self.items:
                item_id = f"{item_id}::{occurrence}"

            item = self._ensure_item(
                item_id,
                item_type="conjugation",
                display=display,
            )
            source = item["sources"].setdefault("textbook", {})
            source["conjugation"] = deepcopy(raw)

            for lesson_id in conjugation_lessons.get(display, []):
                if lesson_id not in item["lessons"]:
                    item["lessons"].append(lesson_id)

            self._remember_representation(
                source="textbook",
                value=display,
                canonical_id=item_id,
                item_type="conjugation",
            )
            count += 1

        # Patterns and skills are merged exactly across lessons while keeping
        # all lesson placements.
        for lesson in data.get("lessons") or []:
            if not isinstance(lesson, dict):
                continue
            lesson_id = _clean(lesson.get("id"))
            practice = lesson.get("practice") or {}
            if not isinstance(practice, dict):
                continue

            for plural, item_type in (
                ("patterns", "pattern"),
                ("skills", "skill"),
            ):
                values = practice.get(plural) or []
                if not isinstance(values, list):
                    continue

                for raw_value in values:
                    display = normalize_surface(raw_value)
                    if not display:
                        continue

                    item_id = self._canonical_id(
                        source="textbook",
                        value=display,
                        item_type=item_type,
                    )
                    item = self._ensure_item(
                        item_id,
                        item_type=item_type,
                        display=display,
                    )
                    if lesson_id and lesson_id not in item["lessons"]:
                        item["lessons"].append(lesson_id)

                    source = item["sources"].setdefault(
                        "textbook",
                        {"entries": []},
                    )
                    entries = source.setdefault("entries", [])
                    entry = {
                        "lesson_id": lesson_id,
                        "kind": item_type,
                        "text": display,
                    }
                    if entry not in entries:
                        entries.append(entry)

                    self._remember_representation(
                        source="textbook",
                        value=display,
                        canonical_id=item_id,
                        item_type=item_type,
                    )
                    count += 1

        self.source_counts["textbook_index"] = count

    def _classify_use_item(self, raw_id: str, display: str) -> str:
        if raw_id.startswith("particle::"):
            return "particle"
        return "observed"

    def _find_existing_for_use(self, display: str) -> str | None:
        normalized = normalize_surface(display)
        # Usage observations may attach to any curriculum grammar-like item.
        for item_id, item in self.items.items():
            if normalize_surface(item.get("display")) == normalized:
                return item_id
        return None

    def _add_use(self, data: dict[str, Any]) -> None:
        count = 0
        for raw_id, raw in (data.get("items") or {}).items():
            if not isinstance(raw, dict):
                continue

            raw_id = _clean(raw_id)
            display = normalize_surface(
                raw.get("grammar") or raw.get("item_id") or raw_id
            )
            if not display:
                continue

            normalized = normalize_surface(display)
            item_id = self.alias_lookup.get(("grammar_use", normalized))
            if not item_id:
                item_id = self._find_existing_for_use(display)

            if not item_id:
                item_type = self._classify_use_item(raw_id, display)
                if item_type == "particle" and raw_id.startswith("particle::"):
                    item_id = raw_id
                else:
                    item_id = _typed_id(item_type, display)
            else:
                item_type = self.items[item_id]["type"]

            item = self._ensure_item(
                item_id,
                item_type=item_type,
                display=display,
            )
            item["use"] = deepcopy(raw)
            lesson_id = _clean(raw.get("lesson_id"))
            if lesson_id and lesson_id not in item["lessons"]:
                item["lessons"].append(lesson_id)

            self._remember_representation(
                source="grammar_use",
                value=display,
                canonical_id=item_id,
                item_type=item["type"],
            )
            count += 1

        self.source_counts["grammar_use_index"] = count

    @staticmethod
    def _candidate_head_keys(value: str) -> list[str]:
        """Return additional conservative candidate keys for grammar heads.

        This is used only for alias suggestions. It never merges automatically.
        Textbook patterns often include a trailing clause placeholder such as
        `#∵`; stripping only that trailing placeholder lets entries like
        `#～ ば、 #∵` suggest `～ば` without collapsing unrelated patterns.
        """
        text = normalize_surface(value)

        keys: list[str] = []

        # Remove a trailing sentence/clause placeholder, along with punctuation
        # immediately before it.
        head = re.sub(
            r"[、,]\s*#∵\s*$",
            "",
            text,
        ).strip()

        if head != text:
            head_key = GrammarProfileBuilder._candidate_key(head)
            if head_key:
                keys.append(head_key)

        return keys

    @staticmethod
    def _candidate_key(value: str) -> str:
        # This is deliberately more permissive than canonical matching because
        # candidates are only suggestions and never merge automatically.
        value = normalize_surface(value)
        value = value.replace("#～", "～")
        value = value.replace("#○○", "N")
        value = value.replace("#∵", "文")
        value = re.sub(r"\[\[|\]\]", "", value)
        value = re.sub(r"\s+", "", value)
        value = value.replace("です", "")
        return value

    def _build_alias_candidates(self) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        canonical_items = [
            item
            for item in self.items.values()
            if item.get("type") in {"grammar", "conjugation", "pattern", "skill", "particle"}
        ]

        for representation in self.representations:
            source = representation["source"]
            value = representation["value"]

            if (source, value) in self.alias_lookup:
                continue

            current_id = representation["canonical_id"]
            value_key = self._candidate_key(value)
            value_keys = [value_key] if value_key else []
            value_keys.extend(self._candidate_head_keys(value))
            value_keys = [key for key in dict.fromkeys(value_keys) if key]
            if not value_keys:
                continue

            suggestions: list[dict[str, Any]] = []
            for item in canonical_items:
                item_id = _clean(item.get("item_id"))
                if not item_id or item_id == current_id:
                    continue

                # Alias candidates are for cross-source identity resolution.
                # Suggestions within the same source are mostly just similar
                # grammar points and create noise.
                item_aliases = item.get("aliases") or {}
                if source in item_aliases:
                    continue

                target_display = item.get("display")
                target_key = self._candidate_key(target_display)
                target_keys = [target_key] if target_key else []
                target_keys.extend(self._candidate_head_keys(target_display))
                target_keys = [key for key in dict.fromkeys(target_keys) if key]
                if not target_keys:
                    continue

                score = 0.0
                for left in value_keys:
                    for right in target_keys:
                        ratio = SequenceMatcher(None, left, right).ratio()
                        containment = (
                            min(len(left), len(right))
                            / max(len(left), len(right))
                            if left in right or right in left
                            else 0.0
                        )
                        score = max(score, ratio, containment)

                if score < 0.62:
                    continue

                suggestions.append(
                    {
                        "canonical_id": item_id,
                        "display": item.get("display"),
                        "type": item.get("type"),
                        "score": round(score, 4),
                    }
                )

            suggestions.sort(key=lambda entry: entry["score"], reverse=True)
            suggestions = suggestions[:5]
            if not suggestions:
                continue

            key = (source, value)
            if key in seen:
                continue
            seen.add(key)

            candidates.append(
                {
                    "source": source,
                    "value": value,
                    "current_id": current_id,
                    "suggested_matches": suggestions,
                }
            )

        return candidates
