from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WritingConfig:
    daily_new_limit: int = 10
    new_fail_cooldown_min: int = 3
    new_fail_cooldown_max: int = 5


@dataclass(frozen=True)
class OutputConfig:
    folder: Path
    textbook_profile: str = "auto/textbook_profile.json"
    wanikani_index: str = "auto/wanikani_index.json"
    anki_index: str = "auto/anki_index.json"
    profile_manifest: str = "auto/profile_manifest.json"
    vocabulary_profile: str = "auto/vocabulary_profile.json"
    writing_profile: str = "manual/writing_profile.json"
    srs_history: str = "manual/srs_history.json"
    grammar_mastery: str = "manual/grammar_mastery.json"
    daily_goals: str = "manual/daily_goals.json"
    daily_goal_schedule: str = "manual/daily_goal_schedule.json"
    grammar_profile: str = "auto/grammar_profile.json"
    knowledge_profile: str = "knowledge_profile.json"


@dataclass(frozen=True)
class ObsidianConfig:
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
    api_key: str = ""
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
    furigana_in_word: bool = False
    split_lines: bool = False


@dataclass(frozen=True)
class AnkiConfig:
    host: str = "http://localhost:8765"
    api_version: int = 6
    timeout_seconds: float = 30.0
    batch_size: int = 500
    decks: tuple[str, ...] = ()
    fields: AnkiFieldConfig = field(default_factory=AnkiFieldConfig)
    deck_fields: dict[str, AnkiFieldConfig] = field(default_factory=dict)


@dataclass(frozen=True)
class BunproConfig:
    email: str = ""
    password: str = ""
    api_url: str = "https://api.bunpro.jp"
    login_url: str = "https://bunpro.jp"
    timeout_seconds: float = 30.0
    include_grammar: bool = True
    include_vocabulary: bool = True



@dataclass(frozen=True)
class AppConfig:
    project_dir: Path
    writing: WritingConfig
    output: OutputConfig
    obsidian: ObsidianConfig
    wanikani: WaniKaniConfig
    anki: AnkiConfig
    bunpro: BunproConfig
