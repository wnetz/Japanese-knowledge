from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import BaseNoteParser
from .markdown import strip_ruby
from .models import KeyNote


class KeyParser(BaseNoteParser):
    note_type = "key"

    def parse(self, *, path: Path, raw_text: str, body: str, frontmatter: dict[str, Any]) -> KeyNote:
        common = self.build_common(path=path, body=body, frontmatter=frontmatter)
        if not frontmatter.get("name") and not frontmatter.get("title"):
            common["title"] = path.stem
        return KeyNote(
            **common,
            key_type=str(frontmatter.get("key_type", "placeholders")),
            definitions=self.extract_definitions(body),
        )

    @staticmethod
    def extract_definitions(body: str) -> dict[str, str]:
        definitions: dict[str, str] = {}
        for raw_line in body.splitlines():
            match = re.match(r"^#\s+(.+?)\s*:\s*(#[^\s]+)\s*$", raw_line.strip())
            if match:
                label, symbol = match.groups()
                definitions[symbol] = strip_ruby(label)
        return definitions
