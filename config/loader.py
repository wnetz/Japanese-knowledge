from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .models import (
    AnkiConfig,
    AnkiFieldConfig,
    AppConfig,
    LoggingConfig,
    ObsidianConfig,
    OutputConfig,
    WaniKaniConfig,
    WaniKaniDownloadConfig,
)


class ConfigError(ValueError):
    """Raised when Knowledge Engine configuration is invalid."""


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


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
    main_path = Path(config_path) if config_path else project_dir / "config.json"
    if not main_path.is_absolute():
        main_path = (project_dir / main_path).resolve()
    local_path = (
        Path(local_config_path)
        if local_config_path
        else main_path.with_name("config.local.json")
    )
    if not local_path.is_absolute():
        local_path = (project_dir / local_path).resolve()

    merged = _deep_merge(
        _read_json(main_path, required=True),
        _read_json(local_path, required=False),
    )

    vault_section = merged.get("vault") or {}
    obsidian_section = merged.get("obsidian") or {}
    output_section = merged.get("output") or {}
    wk_section = merged.get("wanikani") or {}
    wk_download = wk_section.get("download") or {}
    anki_section = merged.get("anki") or {}
    logging_section = merged.get("logging") or {}

    vault_value = obsidian_section.get("vault") or vault_section.get("path")
    if not isinstance(vault_value, str) or not vault_value.strip():
        raise ConfigError("Set vault.path (or obsidian.vault) in config.json")

    output_value = output_section.get("folder") or output_section.get("directory") or "./output"
    if not isinstance(output_value, str):
        raise ConfigError("output.folder must be a string")

    subject_types = wk_section.get("subject_types") or [
        "radical", "kanji", "vocabulary", "kana_vocabulary"
    ]
    if not isinstance(subject_types, list) or not all(isinstance(v, str) for v in subject_types):
        raise ConfigError("wanikani.subject_types must be an array of strings")

    return AppConfig(
        project_dir=project_dir,
        output=OutputConfig(
            folder=_resolve_path(output_value, project_dir),
            grammar_profile=str(
                output_section.get(
                    "grammar_profile",
                    output_section.get("obsidian_index", "grammar_profile.json"),
                )
            ),
            wanikani_index=str(output_section.get("wanikani_index", "wanikani_index.json")),
            anki_index=str(output_section.get("anki_index", "anki_index.json")),
            profile_manifest=str(output_section.get("profile_manifest", "profile_manifest.json")),
            vocabulary_profile=str(
                output_section.get("vocabulary_profile", "vocabulary_profile.json")
            ),
        ),
        obsidian=ObsidianConfig(
            enabled=bool(obsidian_section.get("enabled", True)),
            vault=_resolve_path(vault_value, project_dir),
            knowledge_engine_folder=str(obsidian_section.get("knowledge_engine_folder", "Knowledge Engine")),
            exclude_folders=tuple(obsidian_section.get("exclude_folders", [".obsidian", ".trash"])),
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
            fields=AnkiFieldConfig(
                word=str((anki_section.get("fields") or {}).get("word", "Word")),
                reading=str((anki_section.get("fields") or {}).get("reading", "Word Reading")),
                meaning=str((anki_section.get("fields") or {}).get("meaning", "Word Meaning")),
                pitch_accent=str((anki_section.get("fields") or {}).get("pitch_accent", "Pitch Accent")),
                frequency=str((anki_section.get("fields") or {}).get("frequency", "Frequency")),
            ),
        ),
        logging=LoggingConfig(level=str(logging_section.get("level", "INFO")).upper()),
        raw=merged,
    )
