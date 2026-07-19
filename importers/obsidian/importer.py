from __future__ import annotations

from typing import Any

from config import ObsidianConfig

from .parser import ObsidianParser


class GrammarProfileImporter:
    """Build the grammar profile from the configured Obsidian vault."""

    source_name = "obsidian"

    def __init__(self, config: ObsidianConfig) -> None:
        self.config = config

    def import_data(self) -> dict[str, Any]:
        parser = ObsidianParser(
            vault_path=self.config.vault,
            knowledge_engine_folder=self.config.knowledge_engine_folder,
            exclude_folders=list(self.config.exclude_folders),
            require_note_type=self.config.require_note_type,
            default_note_type=self.config.default_note_type,
        )
        parser.scan()
        return parser.export()


# Backward-compatible alias for callers that have not migrated yet.
ObsidianImporter = GrammarProfileImporter
