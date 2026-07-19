from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BaseNoteParser
from .models import ReferenceNote


class ReferenceParser(BaseNoteParser):
    note_type = "reference"

    def parse(self, *, path: Path, raw_text: str, body: str, frontmatter: dict[str, Any]) -> ReferenceNote:
        common = self.build_common(path=path, body=body, frontmatter=frontmatter)
        return ReferenceNote(**common, sections=self.parse_structured_sections(body))
