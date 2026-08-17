from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OutputConfig:
    folder: Path
    textbook_profile: str = "textbook_profile.json"
    wanikani_index: str = "wanikani_index.json"
    anki_index: str = "anki_index.json"
    profile_manifest: str = "profile_manifest.json"
    vocabulary_profile: str = "vocabulary_profile.json"
    bunpro_index: str = "bunpro_index.json"


@dataclass(frozen=True)
class ObsidianConfig:
    enabled: bool
    vault: Path
    knowledge_engine_folder: str = "Knowledge Engine"
    exclude_folders: tuple[str, ...] = (".obsidian", ".trash")
    require_note_type: bool = False
    default_note_type: str = "reference"


@dataclass(frozen=True)
class WaniKaniDownloadConfig:
    subjects: bool = True
    assignments: bool = True
    review_statistics: bool = True
    user: bool = True
    mnemonics: bool = True
    context_sentences: bool = True


@dataclass(frozen=True)
class WaniKaniConfig:
    enabled: bool
    api_key: str = ""
    api_version: str = "20170710"
    subject_types: tuple[str, ...] = (
        "radical",
        "kanji",
        "vocabulary",
        "kana_vocabulary",
    )
    download: WaniKaniDownloadConfig = field(default_factory=WaniKaniDownloadConfig)


@dataclass(frozen=True)
class AnkiFieldConfig:
    word: str = "Word"
    reading: str = "Word Reading"
    meaning: str = "Word Meaning"
    pitch_accent: str = "Pitch Accent"
    frequency: str = "Frequency"


@dataclass(frozen=True)
class AnkiConfig:
    enabled: bool = False
    host: str = "http://localhost:8765"
    api_version: int = 6
    timeout_seconds: float = 30.0
    batch_size: int = 500
    decks: tuple[str, ...] = ()
    fields: AnkiFieldConfig = field(default_factory=AnkiFieldConfig)


@dataclass(frozen=True)
class BunproConfig:
    enabled: bool = False
    email: str = ""
    password: str = ""
    api_url: str = "https://api.bunpro.jp"
    login_url: str = "https://bunpro.jp"
    timeout_seconds: float = 30.0
    include_grammar: bool = True
    include_vocabulary: bool = True


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"


@dataclass(frozen=True)
class AppConfig:
    project_dir: Path
    output: OutputConfig
    obsidian: ObsidianConfig
    wanikani: WaniKaniConfig
    anki: AnkiConfig
    bunpro: BunproConfig
    logging: LoggingConfig
    raw: dict[str, Any] = field(repr=False, compare=False, default_factory=dict)
