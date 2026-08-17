from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class WikiLink:
    target: str
    alias: str = ""


@dataclass
class Placeholder:
    symbol: str
    meaning: str = "unknown"


@dataclass
class ContentItem:
    type: str
    value: str
    placeholders: list[Placeholder] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)


@dataclass
class Section:
    level: int
    heading: str
    heading_path: list[str]
    items: list[ContentItem] = field(default_factory=list)


@dataclass
class Transformation:
    form: str
    to: str
    by: str


@dataclass
class Practice:
    skills: list[ContentItem] = field(default_factory=list)
    questions: list[ContentItem] = field(default_factory=list)
    responses: list[ContentItem] = field(default_factory=list)
    patterns: list[ContentItem] = field(default_factory=list)
    transformations: list[Transformation] = field(default_factory=list)


@dataclass
class Lesson:
    id: str
    can_do: list[ContentItem] = field(default_factory=list)
    practice: Practice = field(default_factory=Practice)


@dataclass
class GroupMember:
    word: str
    part_of_speech: str = ""
    part_of_speech_name: str = ""
    wikilinks: list[str] = field(default_factory=list)


@dataclass
class GroupSection:
    name: str
    members: list[GroupMember] = field(default_factory=list)


@dataclass
class BaseNote:
    note_type: str
    title: str
    filename: str
    path: str
    folder: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    wikilinks: list[WikiLink] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _remove_empty(asdict(self))


@dataclass
class LessonNote(BaseNote):
    lessons: list[Lesson] = field(default_factory=list)


@dataclass
class ConjugationNote(BaseNote):
    name: str = ""
    targets: list[str] = field(default_factory=list)
    forms: dict[str, str] = field(default_factory=dict)
    transformations: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class VerbFormNote(BaseNote):
    forms: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class GroupNote(BaseNote):
    groups: list[GroupSection] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class KeyNote(BaseNote):
    key_type: str = "placeholders"
    definitions: dict[str, str] = field(default_factory=dict)


@dataclass
class ReferenceNote(BaseNote):
    sections: list[Section] = field(default_factory=list)


def _remove_empty(value: Any) -> Any:
    """Recursively remove empty optional values without deleting meaningful False/0."""
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
