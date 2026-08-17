from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from config import ConfigError, load_config
from core import write_json
from importers.anki import AnkiImporter
from importers.bunpro import BunproImporter
from importers.obsidian import GrammarProfileImporter
from importers.wanikani import WaniKaniImporter
from profile import ProfileBuilder, build_knowledge_profile


def _run_source(
    name: str,
    enabled: bool,
    importer_factory: Callable[[], Any],
    output_path: Path,
) -> dict[str, Any]:
    if not enabled:
        print(f"{name}: disabled")
        return {"enabled": False, "status": "disabled"}

    print(f"{name}: importing...")
    try:
        importer = importer_factory()
        data = importer.import_data()
        write_json(data, output_path)
        errors = data.get("errors", []) if isinstance(data, dict) else []
        status = "completed_with_errors" if errors else "completed"
        print(f"{name}: {status}; wrote {output_path}")
        item_count = data.get("note_count", data.get("subject_count"))
        if item_count is None and isinstance(data.get("counts"), dict):
            item_count = sum(
                value for value in data["counts"].values() if isinstance(value, int)
            )
        return {
            "enabled": True,
            "status": status,
            "output": str(output_path),
            "item_count": item_count,
            "error_count": len(errors),
        }
    except Exception as exc:
        print(f"{name}: failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return {
            "enabled": True,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }


def build_parser() -> argparse.ArgumentParser:
    # Define CLI options for selecting config files used by the profile update run.
    parser = argparse.ArgumentParser(
        description="Refresh configured knowledge sources, then build the vocabulary profile."
    )
    parser.add_argument("--config", default=None, help="Path to config.json")
    parser.add_argument("--local-config", default=None, help="Path to config.local.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config, args.local_config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    output_dir = config.output.folder
    output_dir.mkdir(parents=True, exist_ok=True)

    source_results: dict[str, Any] = {}

    source_results["obsidian"] = _run_source(
        "Grammar profile",
        config.obsidian.enabled,
        lambda: GrammarProfileImporter(config.obsidian),
        output_dir / config.output.textbook_profile,
    )

    def make_wanikani() -> WaniKaniImporter:
        wk = config.wanikani
        if not wk.api_key:
            raise ConfigError(
                "WaniKani is enabled but wanikani.api_key is empty. "
                "Put it in config.local.json."
            )
        return WaniKaniImporter(
            wk.api_key,
            include_user=wk.download.user,
            include_subjects=wk.download.subjects,
            include_assignments=wk.download.assignments,
            include_review_statistics=wk.download.review_statistics,
            include_mnemonics=wk.download.mnemonics,
            include_context_sentences=wk.download.context_sentences,
            subject_types=wk.subject_types,
        )

    source_results["wanikani"] = _run_source(
        "WaniKani",
        config.wanikani.enabled,
        make_wanikani,
        output_dir / config.output.wanikani_index,
    )

    def make_anki() -> AnkiImporter:
        if not config.anki.decks:
            raise ConfigError(
                "Anki is enabled but anki.decks is empty. Add the deck names "
                "to config.json or config.local.json."
            )
        return AnkiImporter(config.anki)

    source_results["anki"] = _run_source(
        "Anki",
        config.anki.enabled,
        make_anki,
        output_dir / config.output.anki_index,
    )

    def make_bunpro() -> BunproImporter:
        bp = config.bunpro
        if not bp.email or not bp.password:
            raise ConfigError(
                "Bunpro is enabled but bunpro.email/password are empty. "
                "Put them in config.local.json."
            )
        return BunproImporter(
            bp.email,
            bp.password,
            api_url=bp.api_url,
            login_url=bp.login_url,
            timeout=bp.timeout_seconds,
            include_grammar=bp.include_grammar,
            include_vocabulary=bp.include_vocabulary,
        )

    source_results["bunpro"] = _run_source(
        "Bunpro",
        config.bunpro.enabled,
        make_bunpro,
        output_dir / config.output.grammar_profile,
    )

    print("Profile: building vocabulary profile...")
    try:
        builder = ProfileBuilder(
            output_dir,
            output_filename=config.output.vocabulary_profile,
        )
        profile = builder.build_and_write()
        print(f"Profile: wrote {builder.output_path}")
        print(builder.statistics.format())
        profile_result = {
            "status": "completed",
            "output": str(builder.output_path),
            "vocabulary_count": profile.metadata.vocabulary_count,
            "confidence_scored_count": profile.metadata.confidence_scored_count,
        }
    except Exception as exc:
        print(f"Profile: failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        profile_result = {
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }

    try:
        knowledge_profile_path = build_knowledge_profile(
            output_dir,
            textbook_filename=config.output.textbook_profile,
            grammar_filename=config.output.grammar_profile,
            vocabulary_filename=config.output.vocabulary_profile,
            output_filename=config.output.knowledge_profile,
        )
        print(f"Knowledge profile: wrote {knowledge_profile_path}")
        knowledge_profile_result = {"status": "completed", "output": str(knowledge_profile_path)}
    except Exception as exc:
        print(f"Knowledge profile: failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        knowledge_profile_result = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}

    manifest = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_folder": str(output_dir),
        "sources": source_results,
        "profile": profile_result,
        "knowledge_profile": knowledge_profile_result,
    }
    manifest_path = write_json(manifest, output_dir / config.output.profile_manifest)
    print(f"Profile manifest: {manifest_path}")

    failed = (
        any(item.get("status") == "failed" for item in source_results.values())
        or profile_result.get("status") == "failed"
        or knowledge_profile_result.get("status") == "failed"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
