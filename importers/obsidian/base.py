from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .markdown import extract_tags, extract_wikilinks, parse_sections, strip_ruby
from .models import BaseNote, ContentItem, Placeholder, Section, WikiLink


class BaseNoteParser:
    note_type = "reference"

    def __init__(self, key_definitions: dict[str, str] | None = None) -> None:
        self.key_definitions = key_definitions or {}

    def parse(self, *, path: Path, raw_text: str, body: str, frontmatter: dict[str, Any]) -> BaseNote:
        return BaseNote(**self.build_common(path=path, body=body, frontmatter=frontmatter))

    def build_common(self, *, path: Path, body: str, frontmatter: dict[str, Any]) -> dict[str, Any]:
        title = str(frontmatter.get("name") or frontmatter.get("title") or "").strip()
        if not title:
            title = self.infer_title(body, path.stem)

        metadata = {
            key: frontmatter.get(key)
            for key in ("book", "chapter", "lesson", "category", "jlpt")
            if frontmatter.get(key) not in (None, "", [])
        }

        return {
            "note_type": self.note_type,
            "title": strip_ruby(title),
            "filename": path.name,
            "path": path.as_posix(),
            "folder": path.parent.as_posix(),
            "frontmatter": frontmatter,
            "tags": extract_tags(body, frontmatter),
            "wikilinks": [WikiLink(**item) for item in extract_wikilinks(body)],
            "metadata": metadata,
        }

    def parse_structured_sections(self, body: str) -> list[Section]:
        result: list[Section] = []
        for section in parse_sections(body):
            items = self.parse_lines(section["lines"])
            if items or section["heading"]:
                result.append(Section(
                    level=section["level"],
                    heading=section["heading"],
                    heading_path=section["heading_path"],
                    items=items,
                ))
        return result

    def parse_lines(self, lines: list[str]) -> list[ContentItem]:
        items: list[ContentItem] = []
        for raw_line in lines:
            content = raw_line.strip()
            if not content:
                continue

            item_type = "note"
            if content.startswith("- "):
                content = content[2:].strip()
                item_type = "list_item"

            if content.startswith("#q"):
                item_type = "question"
                content = content[2:].strip()
            elif content.startswith("#a"):
                item_type = "answer"
                content = content[2:].strip()
            elif "⇒" in content:
                item_type = "skill"
            elif self.extract_placeholders(content):
                item_type = "pattern"

            value = strip_ruby(content)
            items.append(ContentItem(
                type=item_type,
                value=value,
                placeholders=[
                    Placeholder(symbol=symbol, meaning=self.key_definitions.get(symbol, "unknown"))
                    for symbol in self.extract_placeholders(content)
                ],
                wikilinks=[item["target"] for item in extract_wikilinks(content)],
            ))
        return items

    def infer_title(self, body: str, fallback: str) -> str:
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            heading = re.match(r"^#{1,6}\s+(.+)$", stripped)
            if heading:
                candidate = heading.group(1).strip()
                if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:", candidate):
                    return strip_ruby(candidate)
            if not stripped.startswith(("-", "#")):
                return strip_ruby(stripped)
        return fallback

    def extract_placeholders(self, text: str) -> list[str]:
        """Return placeholder keys in reading order without parent-key overlap.

        Keys may be hierarchical, for example ``#☆``, ``#☆/い``, and
        ``#☆/な``.  A specific key must not also be reported as its shorter
        parent merely because the parent is a substring of it.
        """
        known = sorted(self.key_definitions, key=len, reverse=True)

        # Include the built-in symbols for notes parsed without a key file.
        # The optional /suffix supports hierarchical adjective keys while
        # remaining backward compatible with the existing placeholders.
        fallback = re.findall(r"#(?:○○|□□|■■|△|～|☆)(?:/[いな])?", text)
        candidates = list(dict.fromkeys([*known, *fallback]))
        if not candidates:
            return []

        # Longest alternatives first ensures #☆/い wins over #☆ at the same
        # position.  Consuming one match at a time prevents overlapping hits.
        pattern = re.compile("|".join(re.escape(symbol) for symbol in sorted(candidates, key=len, reverse=True)))
        found: list[str] = []
        for match in pattern.finditer(text):
            symbol = match.group(0)
            if symbol not in found:
                found.append(symbol)
        return found
