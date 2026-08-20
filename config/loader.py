from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .models import (
    AnkiConfig,
    AnkiFieldConfig,
    AppConfig,
    BunproConfig,
    LoggingConfig,
    ObsidianConfig,
    OutputConfig,
    WaniKaniConfig,
    WaniKaniDownloadConfig,
    WritingConfig,
)


class ConfigError(ValueError):
    """Raised when Knowledge Engine configuration is invalid."""

# merge two dictionaries recursively, with values from the second overriding those from the first
def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        # if both values are dictionaries, keep decending into them; otherwise, override the value from the base with the value from the override   
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result

# read a JSON file and return its contents as a dictionary, raising ConfigError if the file is missing or invalid
def _read_json(path: Path, *, required: bool) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise ConfigError(f"Configuration file not found: {path}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Configuration root must be an object: {path}")
    return data


def _resolve_path(value: str, project_dir: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (project_dir / path).resolve()


def load_config(
    config_path: str | Path | None = None,
    local_config_path: str | Path | None = None,
) -> AppConfig:
    project_dir = Path(__file__).resolve().parents[1]
    #path for main config.json
    main_path = Path(config_path) if config_path else project_dir / "config.json"
    #if main_path is not absolute, resolve it relative to project_dir
    if not main_path.is_absolute():
        main_path = (project_dir / main_path).resolve()
    #path for local config.local.json
    local_path = (
        Path(local_config_path)
        if local_config_path
        else main_path.with_name("config.local.json")
    )
    #if local_path is not absolute, resolve it relative to project_dir
    if not local_path.is_absolute():
        local_path = (project_dir / local_path).resolve()
    #merge the main and local config files, with local taking precedence
    merged = _deep_merge(
        _read_json(main_path, required=True),
        _read_json(local_path, required=False),
    )
    #file paths to be used in the output section of the config
    output_section = merged.get("output") or {}
    writing_section = merged.get("writing") or {}
    #data for obsidian import
    obsidian_section = merged.get("obsidian") or {}
    #data for wanikani import
    wk_section = merged.get("wanikani") or {}
    #data for wanikani download options
    wk_download = wk_section.get("download") or {}
    #data for anki import
    anki_section = merged.get("anki") or {}
    bunpro_section = merged.get("bunpro") or {}
    logging_section = merged.get("logging") or {}

    vault_value = obsidian_section.get("path")
    if not isinstance(vault_value, str) or not vault_value.strip():
        raise ConfigError("Set obsidian.path in config.json")
    #get the output folder. generally this is set to "./output"
    output_value = output_section.get("folder") or "./output"
    if not isinstance(output_value, str):
        raise ConfigError("output.folder must be a string")
    #list of things to import from wanikani
    subject_types = wk_section.get("subject_types") or [
        "radical", "kanji", "vocabulary", "kana_vocabulary"
    ]
    if not isinstance(subject_types, list) or not all(isinstance(v, str) for v in subject_types):
        raise ConfigError("wanikani.subject_types must be an array of strings")

    def _anki_field_config(values: dict[str, Any] | None) -> AnkiFieldConfig:
        values = values or {}
        return AnkiFieldConfig(
            word=str(values.get("word", "Word")),
            reading=str(values.get("reading", "Word Reading")),
            meaning=str(values.get("meaning", "Word Meaning")),
            pitch_accent=str(values.get("pitch_accent", "Pitch Accent")),
            frequency=str(values.get("frequency", "Frequency")),
            furigana_in_word=bool(values.get("furigana_in_word", False)),
            split_lines=bool(values.get("split_lines", False)),
        )

    deck_fields_raw = anki_section.get("deck_fields") or {}
    if not isinstance(deck_fields_raw, dict):
        raise ConfigError("anki.deck_fields must be an object keyed by deck name")
    deck_fields = {
        str(deck_name): _anki_field_config(values if isinstance(values, dict) else {})
        for deck_name, values in deck_fields_raw.items()
    }

    return AppConfig(
        project_dir=project_dir,
        writing=WritingConfig(
            daily_new_limit=max(
                0,
                int(writing_section.get("daily_new_limit", 10)),
            ),
            new_fail_cooldown_min=max(
                0,
                int(writing_section.get("new_fail_cooldown_min", 3)),
            ),
            new_fail_cooldown_max=max(
                0,
                int(writing_section.get("new_fail_cooldown_max", 5)),
            ),
        ),
        output=OutputConfig(
            folder=_resolve_path(output_value, project_dir),
            textbook_profile=    str(output_section.get("textbook_profile", "auto/textbook_profile.json")),
            wanikani_index=     str(output_section.get("wanikani_index", "auto/wanikani_index.json")),
            anki_index=         str(output_section.get("anki_index", "auto/anki_index.json")),
            profile_manifest=   str(output_section.get("profile_manifest", "auto/profile_manifest.json")),
            vocabulary_profile= str(output_section.get("vocabulary_profile", "auto/vocabulary_profile.json")),
            writing_profile=    str(output_section.get("writing_profile", "manual/writing_profile.json")),
            srs_history=        str(output_section.get("srs_history", "manual/srs_history.json")),
            grammar_profile=        str(output_section.get("grammar_profile", "auto/grammar_profile.json")),
            knowledge_profile=      str(output_section.get("knowledge_profile", "knowledge_profile.json")),
        ),
        obsidian=ObsidianConfig(
            enabled=bool(obsidian_section.get("enabled", True)),
            vault=_resolve_path(vault_value, project_dir),
            #holds path to the key in the obsidian vault for linking
            knowledge_engine_folder=str(obsidian_section.get("knowledge_engine_folder", "Knowledge Engine")),
            exclude_folders=tuple(obsidian_section.get("exclude_folders", [".obsidian", ".trash"])),
            #for handling when note_type is missing in a note
            require_note_type=bool(obsidian_section.get("require_note_type", False)),
            default_note_type=str(obsidian_section.get("default_note_type", "reference")),
        ),
        wanikani=WaniKaniConfig(
            enabled=bool(wk_section.get("enabled", False)),
            api_key=str(wk_section.get("api_key", "")).strip(),
            api_version=str(wk_section.get("api_version", "20170710")),
            subject_types=tuple(subject_types),
            download=WaniKaniDownloadConfig(
                subjects=bool(wk_download.get("subjects", wk_section.get("download_subjects", True))),
                assignments=bool(wk_download.get("assignments", wk_section.get("download_assignments", True))),
                review_statistics=bool(wk_download.get("review_statistics", wk_section.get("download_reviews", True))),
                user=bool(wk_download.get("user", True)),
                mnemonics=bool(wk_download.get("mnemonics", True)),
                context_sentences=bool(wk_download.get("context_sentences", True)),
            ),
        ),
        anki=AnkiConfig(
            enabled=bool(anki_section.get("enabled", False)),
            host=str(anki_section.get("host", "http://localhost:8765")),
            api_version=int(anki_section.get("api_version", 6)),
            timeout_seconds=float(anki_section.get("timeout_seconds", 30)),
            batch_size=max(1, int(anki_section.get("batch_size", 500))),
            decks=tuple(str(value) for value in anki_section.get("decks", [])),
            fields=_anki_field_config(anki_section.get("fields") or {}),
            deck_fields=deck_fields,
        ),
        bunpro=BunproConfig(
            enabled=bool(bunpro_section.get("enabled", False)),
            email=str(bunpro_section.get("email", "")).strip(),
            password=str(bunpro_section.get("password", "")),
            api_url=str(bunpro_section.get("api_url", "https://api.bunpro.jp")).rstrip("/"),
            login_url=str(bunpro_section.get("login_url", "https://bunpro.jp")).rstrip("/"),
            timeout_seconds=float(bunpro_section.get("timeout_seconds", 30)),
            include_grammar=bool(bunpro_section.get("include_grammar", True)),
            include_vocabulary=bool(bunpro_section.get("include_vocabulary", True)),
        ),
        logging=LoggingConfig(level=str(logging_section.get("level", "INFO")).upper()),
        raw=merged,
    )
