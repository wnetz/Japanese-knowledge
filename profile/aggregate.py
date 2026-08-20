from pathlib import Path
from core import read_json, write_json

def build_knowledge_profile(output_dir: Path, *, textbook_filename="auto/textbook_profile.json", grammar_filename="auto/grammar_profile.json", vocabulary_filename="auto/vocabulary_profile.json", output_filename="knowledge_profile.json") -> Path:
    return write_json({
        "textbook_profile": read_json(output_dir / textbook_filename),
        "grammar_profile": read_json(output_dir / grammar_filename),
        "vocabulary_profile": read_json(output_dir / vocabulary_filename),
    }, output_dir / output_filename)
