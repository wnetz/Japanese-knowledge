from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BaseNoteParser
from .markdown import extract_wikilinks, parse_sections, strip_ruby
from .models import GroupMember, GroupNote, GroupSection


class GroupParser(BaseNoteParser):
    note_type = "group"

    def parse(self, *, path: Path, raw_text: str, body: str, frontmatter: dict[str, Any]) -> GroupNote:
        common = self.build_common(path=path, body=body, frontmatter=frontmatter)
        groups: list[GroupSection] = []
        notes: list[str] = []

        for section in parse_sections(body):
            heading = section["heading"].strip()
            if heading.casefold() == "notes":
                notes.extend(self._parse_notes(section["lines"]))
                continue

            members = [member for line in section["lines"] if (member := self._parse_member(line))]
            if members:
                group_name = heading or str(frontmatter.get("name") or path.stem)
                groups.append(GroupSection(name=group_name, members=members))

        return GroupNote(**common, groups=groups, notes=notes)

    def _parse_member(self, raw_line: str) -> GroupMember | None:
        line = raw_line.strip()
        if not line.startswith("- "):
            return None

        content = line[2:].strip()
        word_raw, separator, symbol_raw = content.partition("::")
        word = strip_ruby(word_raw.strip())
        if not word:
            return None

        symbol = symbol_raw.strip() if separator else ""
        return GroupMember(
            word=word,
            part_of_speech=symbol,
            part_of_speech_name=self.key_definitions.get(symbol, "") if symbol else "",
            wikilinks=[item["target"] for item in extract_wikilinks(word_raw)],
        )

    @staticmethod
    def _parse_notes(lines: list[str]) -> list[str]:
        notes: list[str] = []
        paragraph: list[str] = []

        def flush() -> None:
            if paragraph:
                notes.append(strip_ruby(" ".join(paragraph).strip()))
                paragraph.clear()

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                flush()
                continue
            if line.startswith("- "):
                flush()
                notes.append(strip_ruby(line[2:].strip()))
            else:
                paragraph.append(line)
        flush()
        return notes
