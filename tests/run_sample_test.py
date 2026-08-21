from collections import Counter
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from input.obsidian import ObsidianParser


def main() -> None:
    vault = Path(__file__).resolve().parent / "sample_vault"
    parser = ObsidianParser(vault, knowledge_engine_folder="Knowledge Engine")
    notes = parser.scan()
    result = parser.export()

    counts = Counter(note.note_type for note in notes)

    assert len(notes) == 15
    assert counts["key"] == 3
    assert counts["lesson"] == 3
    assert counts["conjugation"] == 6
    assert counts["group"] == 3
    assert result["key_definitions"]["#○○"] == "名詞"
    assert result["key_definitions"]["#△"] == "番号"
    assert result["lessons"]
    lesson = result["lessons"][0]
    assert lesson["practice"]["questions"]
    assert lesson["practice"]["responses"]
    assert lesson["practice"]["patterns"]

    print("All sample tests passed.")
    print(dict(counts))
    print(result["key_definitions"])


if __name__ == "__main__":
    main()
