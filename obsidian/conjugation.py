from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import BaseNoteParser
from .markdown import PROPERTY_RE, strip_ruby
from .models import ConjugationNote


VERB_GROUP_HEADING_RE = re.compile(
    r"^#{1,6}\s+(?:#\s*)?\[\[[^\]#]+#(V[123])(?:\|[^\]]+)?\]\]\s*$",
    re.IGNORECASE,
)


class ConjugationParser(BaseNoteParser):
    note_type = "conjugation"

    def parse(self, *, path: Path, raw_text: str, body: str, frontmatter: dict[str, Any]) -> ConjugationNote:
        common = self.build_common(path=path, body=body, frontmatter=frontmatter)
        forms: dict[str, str] = {}
        transformations: dict[str, list[str]] = {}
        current_group: str | None = None

        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            group_match = VERB_GROUP_HEADING_RE.match(line)
            if group_match:
                current_group = group_match.group(1).upper()
                transformations.setdefault(current_group, [])
                continue

            property_match = PROPERTY_RE.match(line)
            if property_match:
                key, value = property_match.groups()
                forms[key] = strip_ruby(value).strip()
                current_group = None
                continue

            if line.startswith("#"):
                current_group = None
                continue

            if current_group:
                value = strip_ruby(line)
                if value.startswith("- "):
                    value = value[2:].strip()
                if value:
                    transformations[current_group].append(value)

        name = str(frontmatter.get("name") or common["title"]).strip()
        return ConjugationNote(
            **common,
            name=strip_ruby(name),
            forms=forms,
            transformations=transformations,
        )
