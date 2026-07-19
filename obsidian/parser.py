from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .conjugation import ConjugationParser
from .group import GroupParser
from .key import KeyParser
from .lesson import LessonParser
from .markdown import parse_frontmatter
from .models import BaseNote, KeyNote
from .reference import ReferenceParser
from .verb_form import VerbFormParser


class ObsidianParser:
    """
    Vault-level parser for William's Japanese Knowledge Engine.

    Workflow:
    1. Scan every Markdown file recursively.
    2. Load note_type: key files first.
    3. Merge key definitions.
    4. Parse all remaining notes using their explicit note_type.
    """

    SUPPORTED_NOTE_TYPES = {
        "lesson",
        "conjugation",
        "group",
        "key",
        "reference",
        "verb form",
    }

    def __init__(
        self,
        vault_path: str | Path,
        *,
        knowledge_engine_folder: str = "Knowledge Engine",
        exclude_folders: list[str] | None = None,
        require_note_type: bool = False,
        default_note_type: str = "reference",
    ) -> None:
        self.vault_path = Path(vault_path).expanduser()
        self.knowledge_engine_folder = knowledge_engine_folder
        self.exclude_folders = set(exclude_folders or [".obsidian", ".trash"])
        self.require_note_type = require_note_type
        self.default_note_type = default_note_type

        self.key_definitions: dict[str, str] = {}
        self.notes: list[BaseNote] = []
        self.errors: list[dict[str, str]] = []

    @classmethod
    def from_config(cls, config_path: str | Path) -> "ObsidianParser":
        config_path = Path(config_path).expanduser().resolve()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        obsidian = config.get("obsidian", {})

        vault = Path(obsidian["vault"]).expanduser()
        if not vault.is_absolute():
            vault = (config_path.parent / vault).resolve()

        return cls(
            vault_path=vault,
            knowledge_engine_folder=obsidian.get(
                "knowledge_engine_folder",
                "Knowledge Engine",
            ),
            exclude_folders=obsidian.get(
                "exclude_folders",
                [".obsidian", ".trash"],
            ),
            require_note_type=bool(
                obsidian.get("require_note_type", False)
            ),
            default_note_type=str(
                obsidian.get("default_note_type", "reference")
            ),
        )

    def scan(self) -> list[BaseNote]:
        if not self.vault_path.exists():
            raise FileNotFoundError(f"Vault does not exist: {self.vault_path}")
        if not self.vault_path.is_dir():
            raise NotADirectoryError(f"Vault path is not a folder: {self.vault_path}")

        self.notes = []
        self.errors = []
        self.key_definitions = {}

        files = self._find_markdown_files()
        parsed_headers = [self._read_header(path) for path in files]

        key_files = [
            item for item in parsed_headers
            if item["note_type"] == "key"
        ]
        other_files = [
            item for item in parsed_headers
            if item["note_type"] != "key"
        ]

        # Knowledge Engine key files are parsed first.
        key_files.sort(
            key=lambda item: (
                0 if self._is_in_knowledge_engine(item["path"]) else 1,
                item["path"].as_posix().lower(),
            )
        )

        for item in key_files:
            self._parse_and_store(item)

        for item in other_files:
            self._parse_and_store(item)

        return self.notes

    def parse_file(self, path: str | Path) -> BaseNote:
        path = Path(path)
        header = self._read_header(path)
        return self._parse_one(header)

    def export(self) -> dict[str, Any]:
        """Export the compact grammar knowledge profile consumed by Alex.

        Parsing metadata stays internal. The exported JSON contains only the
        grammar data itself, organized by knowledge type.
        """
        conjugations: list[dict[str, Any]] = []
        verb_forms: list[dict[str, list[str]]] = []
        groups: list[dict[str, Any]] = []
        lessons: list[dict[str, Any]] = []

        for note in self.notes:
            if note.note_type == "conjugation":
                item: dict[str, Any] = {
                    "name": getattr(note, "name", ""),
                    "targets": getattr(note, "targets", []),
                    "forms": getattr(note, "forms", {}),
                }
                transformations = getattr(note, "transformations", {})
                if transformations:
                    item["transformations"] = transformations
                conjugations.append(self._remove_empty(item))

            elif note.note_type == "verb form":
                forms = getattr(note, "forms", {})
                if forms:
                    verb_forms.append(forms)

            elif note.note_type == "group":
                group_item: dict[str, Any] = {
                    "name": note.title,
                    "groups": [
                        {
                            "name": section.name,
                            "members": [
                                self._remove_empty({
                                    "word": member.word,
                                    "part_of_speech": member.part_of_speech,
                                })
                                for member in section.members
                            ],
                        }
                        for section in getattr(note, "groups", [])
                    ],
                    "notes": getattr(note, "notes", []),
                }
                groups.append(self._remove_empty(group_item))

            elif note.note_type == "lesson":
                for lesson in getattr(note, "lessons", []):
                    practice = self._remove_empty({
                        "skills": [item.value for item in lesson.practice.skills],
                        "questions": [item.value for item in lesson.practice.questions],
                        "responses": [item.value for item in lesson.practice.responses],
                        "patterns": [item.value for item in lesson.practice.patterns],
                    })
                    lesson_item = {
                        "id": lesson.id,
                        "can_do": [item.value for item in lesson.can_do],
                        "practice": practice,
                    }
                    lessons.append(self._remove_empty(lesson_item))

        return {
            "key_definitions": self.key_definitions,
            "conjugations": conjugations,
            "verb_forms": verb_forms,
            "groups": groups,
            "lessons": lessons,
        }

    @staticmethod
    def _remove_empty(value: Any) -> Any:
        if isinstance(value, dict):
            cleaned = {
                key: ObsidianParser._remove_empty(item)
                for key, item in value.items()
            }
            return {
                key: item
                for key, item in cleaned.items()
                if item not in (None, "", [], {})
            }
        if isinstance(value, list):
            return [ObsidianParser._remove_empty(item) for item in value]
        return value

    def save_json(self, output_path: str | Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.export(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

    def _find_markdown_files(self) -> list[Path]:
        result: list[Path] = []
        for path in self.vault_path.rglob("*.md"):
            if any(part in self.exclude_folders for part in path.relative_to(self.vault_path).parts):
                continue
            result.append(path)
        return sorted(result)

    def _read_header(self, path: Path) -> dict[str, Any]:
        raw_text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter, body = parse_frontmatter(raw_text)

        note_type = str(
            frontmatter.get("note_type")
            or frontmatter.get("not_type")  # temporary typo compatibility
            or ""
        ).strip().lower()

        if not note_type:
            if self.require_note_type:
                raise ValueError(f"Missing note_type in {path}")
            note_type = self.default_note_type

        if note_type not in self.SUPPORTED_NOTE_TYPES:
            raise ValueError(
                f"Unsupported note_type '{note_type}' in {path}. "
                f"Supported: {sorted(self.SUPPORTED_NOTE_TYPES)}"
            )

        return {
            "path": path,
            "raw_text": raw_text,
            "body": body,
            "frontmatter": frontmatter,
            "note_type": note_type,
        }

    def _parse_and_store(self, item: dict[str, Any]) -> None:
        try:
            note = self._parse_one(item)
            self.notes.append(note)

            if isinstance(note, KeyNote):
                self.key_definitions.update(note.definitions)

        except Exception as exc:
            self.errors.append({
                "path": str(item.get("path", "")),
                "error": f"{type(exc).__name__}: {exc}",
            })

    def _parse_one(self, item: dict[str, Any]) -> BaseNote:
        note_type = item["note_type"]
        parser = self._make_parser(note_type)

        note = parser.parse(
            path=item["path"].relative_to(self.vault_path)
            if item["path"].is_relative_to(self.vault_path)
            else item["path"],
            raw_text=item["raw_text"],
            body=item["body"],
            frontmatter=item["frontmatter"],
        )

        return note

    def _make_parser(self, note_type: str):
        parser_map = {
            "lesson": LessonParser,
            "conjugation": ConjugationParser,
            "group": GroupParser,
            "key": KeyParser,
            "reference": ReferenceParser,
            "verb form": VerbFormParser,
        }
        return parser_map[note_type](self.key_definitions)

    def _is_in_knowledge_engine(self, path: Path) -> bool:
        try:
            relative = path.relative_to(self.vault_path)
        except ValueError:
            return False
        return self.knowledge_engine_folder in relative.parts
