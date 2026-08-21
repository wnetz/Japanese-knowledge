from pathlib import Path

from core import read_json, write_json


def build_knowledge_profile(
    output_dir: Path,
    *,
    grammar_filename: str = "auto/grammar_profile.json",
    vocabulary_filename: str = "auto/vocabulary_profile.json",
    output_filename: str = "knowledge_profile.json",
) -> Path:
    """Build the compact knowledge summary consumed by downstream tools."""
    return write_json(
        {
            "grammar_profile": read_json(output_dir / grammar_filename),
            "vocabulary_profile": read_json(output_dir / vocabulary_filename),
        },
        output_dir / output_filename,
    )
