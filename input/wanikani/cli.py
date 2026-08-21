from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config import ConfigError, load_config
from core import write_json

from .client import WaniKaniAPIError
from .importer import WaniKaniImporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import WaniKani data using Knowledge Engine config files.")
    parser.add_argument("--config", default=None, help="Path to config.json")
    parser.add_argument("--local-config", default=None, help="Path to config.local.json")
    parser.add_argument("-o", "--output", default=None, help="Override output JSON path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config, args.local_config)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    wk = config.wanikani
    if not wk.api_key:
        print("wanikani.api_key is empty.", file=sys.stderr)
        return 2

    importer = WaniKaniImporter(
        wk.api_key,
        include_user=wk.download.user,
        include_subjects=wk.download.subjects,
        include_assignments=wk.download.assignments,
        include_review_statistics=wk.download.review_statistics,
        include_mnemonics=wk.download.mnemonics,
        include_context_sentences=wk.download.context_sentences,
        subject_types=wk.subject_types,
    )
    output = Path(args.output) if args.output else config.output.folder / config.output.wanikani_index
    try:
        write_json(importer.import_data(), output)
    except WaniKaniAPIError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Wrote {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
