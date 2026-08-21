from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import BaseNoteParser
from .markdown import parse_sections
from .models import ContentItem, Lesson, LessonNote, Practice, Transformation


LESSON_ID_RE = re.compile(r"\d+(?:-\d+)+")
PRACTICE_HEADINGS = {"宿題", "教科書"}


class LessonParser(BaseNoteParser):
    note_type = "lesson"

    def parse(
        self,
        *,
        path: Path,
        raw_text: str,
        body: str,
        frontmatter: dict[str, Any],
    ) -> LessonNote:
        common = self.build_common(path=path, body=body, frontmatter=frontmatter)
        lessons = self._parse_lessons(body)

        frontmatter_lesson = str(frontmatter.get("lesson", "")).strip()
        if frontmatter_lesson and not any(item.id == frontmatter_lesson for item in lessons):
            lessons.insert(0, Lesson(id=frontmatter_lesson))

        return LessonNote(**common, lessons=lessons)

    def _parse_lessons(self, body: str) -> list[Lesson]:
        lessons: list[Lesson] = []
        current: Lesson | None = None

        for section in parse_sections(body):
            heading = section["heading"].strip()
            level = section["level"]

            if level == 1 and LESSON_ID_RE.fullmatch(heading):
                current = Lesson(id=heading)
                lessons.append(current)
                continue

            if current is None:
                continue

            items = self.parse_lines(section["lines"])
            if level == 2 and heading.casefold().replace(" ", "") == "cando":
                current.can_do.extend(self._as_type(items, "can_do"))
            elif level == 2 and heading in PRACTICE_HEADINGS:
                self._add_practice_items(current.practice, items)

        return lessons

    @staticmethod
    def _as_type(items: list[ContentItem], item_type: str) -> list[ContentItem]:
        for item in items:
            item.type = item_type
        return items

    TRANSFORMATION_RE = re.compile(r"^(.+?)\s+(#→[^\s]+)\s+(.+?)$")

    def _parse_transformation(self, value: str) -> Transformation | None:
        match = self.TRANSFORMATION_RE.fullmatch(value.strip())
        if not match:
            return None

        form, marker, target = (part.strip() for part in match.groups())
        by = self.key_definitions.get(marker, marker.removeprefix("#→"))
        if not form or not target or not by:
            return None
        return Transformation(form=form, to=target, by=by)

    def _add_practice_items(self, practice: Practice, items: list[ContentItem]) -> None:
        for item in items:
            transformation = self._parse_transformation(item.value)
            if transformation is not None:
                practice.transformations.append(transformation)
            elif item.type == "question":
                practice.questions.append(item)
            elif item.type == "answer":
                item.type = "response"
                practice.responses.append(item)
            elif item.type == "pattern":
                practice.patterns.append(item)
            else:
                item.type = "skill"
                practice.skills.append(item)
