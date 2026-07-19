from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import BaseNoteParser
from .markdown import strip_ruby
from .models import VerbFormNote


VERB_GROUP_RE = re.compile(r"^#{1,6}\s+(V[123])\s*:?\s*$", re.IGNORECASE)


class VerbFormParser(BaseNoteParser):
    note_type = "verb form"

    def parse(self, *, path: Path, raw_text: str, body: str, frontmatter: dict[str, Any]) -> VerbFormNote:
        common = self.build_common(path=path, body=body, frontmatter=frontmatter)
        forms: dict[str, list[str]] = {}
        current_group: str | None = None

        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            group_match = VERB_GROUP_RE.match(line)
            if group_match:
                current_group = group_match.group(1).upper()
                forms.setdefault(current_group, [])
                continue

            if line.startswith("#"):
                current_group = None
                continue

            if current_group:
                value = strip_ruby(line)
                if value.startswith("- "):
                    value = value[2:].strip()
                if value:
                    forms[current_group].append(value)

        return VerbFormNote(**common, forms=forms)
