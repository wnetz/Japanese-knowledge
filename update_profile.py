from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from config import ConfigError, load_config
from core import write_json
from input.anki import AnkiImporter
from input.bunpro import BunproImporter
from input.obsidian import GrammarProfileImporter
from input.wanikani import WaniKaniImporter
from profile import ProfileBuilder, build_knowledge_profile
from history import capture_daily_srs_snapshot


def progress(message: str) -> None:
    """Print one progress line immediately for GUI/CLI consumers."""
    print(message, flush=True)


def _refresh_source(
    name: str,
    importer_factory: Callable[[], Any],
    output_path: Path,
) -> dict[str, Any]:
    progress(f"{name}: importing...")
    try:
        importer = importer_factory()
        data = importer.import_data()
        write_json(data, output_path)
        errors = data.get("errors", []) if isinstance(data, dict) else []
        status = "completed_with_errors" if errors else "completed"
        progress(f"{name}: {status}; wrote {output_path}")
        item_count = data.get("note_count", data.get("subject_count"))
        if item_count is None and isinstance(data.get("counts"), dict):
            item_count = sum(
                value for value in data["counts"].values() if isinstance(value, int)
            )
        return {
            "refreshed": True,
            "status": status,
            "output": str(output_path),
            "item_count": item_count,
            "error_count": len(errors),
        }
    except Exception as exc:
        print(
            f"{name}: failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return {
            "refreshed": True,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _preserve_source(name: str, output_path: Path) -> dict[str, Any]:
    progress(f"{name}: not selected; preserving {output_path}")
    return {
        "refreshed": False,
        "status": "preserved",
        "output": str(output_path),
    }


def build_parser() -> argparse.ArgumentParser:
    # Define CLI options for selecting config files used by the profile update run.
    parser = argparse.ArgumentParser(
        description="Refresh configured knowledge sources, then build the vocabulary profile."
    )
    parser.add_argument("--config", default=None, help="Path to config.json")
    parser.add_argument("--local-config", default=None, help="Path to config.local.json")
    parser.add_argument(
        "--sources",
        default="anki,wanikani,bunpro",
        help=(
            "Comma-separated external sources to refresh. "
            "Supported: anki, wanikani, bunpro. "
            "Unselected source index files are preserved."
        ),
    )
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
    (output_dir / "auto").mkdir(parents=True, exist_ok=True)
    (output_dir / "manual").mkdir(parents=True, exist_ok=True)

    supported_sources = {"anki", "wanikani", "bunpro"}
    selected_sources = {
        value.strip().lower()
        for value in str(args.sources).split(",")
        if value.strip()
    }
    unknown_sources = selected_sources - supported_sources
    if unknown_sources:
        print(
            "Unknown source(s): " + ", ".join(sorted(unknown_sources)),
            file=sys.stderr,
        )
        return 2

    source_results: dict[str, Any] = {}

    source_results["obsidian"] = _refresh_source(
        "Obsidian",
        lambda: GrammarProfileImporter(config.obsidian),
        output_dir / config.output.textbook_profile,
    )

    def make_wanikani() -> WaniKaniImporter:
        wk = config.wanikani
        if not wk.api_key:
            raise ConfigError(
                "wanikani.api_key is empty. "
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

    wanikani_output = output_dir / config.output.wanikani_index
    source_results["wanikani"] = (
        _refresh_source("WaniKani", make_wanikani, wanikani_output)
        if "wanikani" in selected_sources
        else _preserve_source("WaniKani", wanikani_output)
    )

    def make_anki() -> AnkiImporter:
        if not config.anki.decks:
            raise ConfigError(
                "anki.decks is empty. Add the deck names "
                "to config.json or config.local.json."
            )
        return AnkiImporter(config.anki)

    anki_output = output_dir / config.output.anki_index
    source_results["anki"] = (
        _refresh_source("Anki", make_anki, anki_output)
        if "anki" in selected_sources
        else _preserve_source("Anki", anki_output)
    )

    def make_bunpro() -> BunproImporter:
        bp = config.bunpro
        if not bp.email or not bp.password:
            raise ConfigError(
                "bunpro.email/password are empty. "
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

    bunpro_output = output_dir / config.output.grammar_profile
    source_results["bunpro"] = (
        _refresh_source("Bunpro", make_bunpro, bunpro_output)
        if "bunpro" in selected_sources
        else _preserve_source("Bunpro", bunpro_output)
    )

    progress("Profile: building vocabulary profile...")
    try:
        builder = ProfileBuilder(
            output_dir,
            output_filename=config.output.vocabulary_profile,
            source_files={
                "wanikani": config.output.wanikani_index,
                "anki": config.output.anki_index,
                "migaku": "manual/migaku_known_words.json",
            },
            writable_kanji_filename="manual/writable_kanji.json",
        )
        profile = builder.build_and_write()
        progress(f"Profile: wrote {builder.output_path}")
        progress(builder.statistics.format())
        profile_result = {
            "status": "completed",
            "output": str(builder.output_path),
            "vocabulary_count": profile.metadata.vocabulary_count,
            "confidence_scored_count": profile.metadata.confidence_scored_count,
        }
    except Exception as exc:
        print(f"Profile: failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
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
        progress(f"Knowledge profile: wrote {knowledge_profile_path}")
        knowledge_profile_result = {"status": "completed", "output": str(knowledge_profile_path)}
    except Exception as exc:
        print(f"Knowledge profile: failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
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
    progress(f"Profile manifest: {manifest_path}")

    try:
        history_path = capture_daily_srs_snapshot(
            history_path=output_dir / config.output.srs_history,
            wanikani_path=output_dir / config.output.wanikani_index,
            anki_path=output_dir / config.output.anki_index,
            bunpro_path=output_dir / config.output.grammar_profile,
            writing_path=output_dir / config.output.writing_profile,
        )
        progress(f"SRS history: updated {history_path}")
    except Exception as exc:
        # History is valuable, but a logging problem should not destroy a
        # successful source/profile update.
        print(
            f"SRS history: failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )

    failed = (
        any(item.get("status") == "failed" for item in source_results.values())
        or profile_result.get("status") == "failed"
        or knowledge_profile_result.get("status") == "failed"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
