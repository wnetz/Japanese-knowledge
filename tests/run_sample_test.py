from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from importers.obsidian import ObsidianParser


def main() -> None:
    vault = Path(__file__).resolve().parent / "sample_vault"
    parser = ObsidianParser(vault, knowledge_engine_folder="Knowledge Engine")
    parser.scan()
    result = parser.export()

    assert result["note_count"] == 15
    assert result["counts_by_type"]["key"] == 3
    assert result["counts_by_type"]["lesson"] == 3
    assert result["counts_by_type"]["conjugation"] == 6
    assert result["counts_by_type"]["group"] == 3
    assert result["key_definitions"]["#○○"] == "名詞"
    assert result["key_definitions"]["#△"] == "番号"

    lesson_note = next(note for note in result["notes"] if note["note_type"] == "lesson")
    assert lesson_note["lessons"]
    lesson = lesson_note["lessons"][0]
    assert lesson["practice"]["questions"]
    assert lesson["practice"]["responses"]
    assert lesson["practice"]["patterns"]

    print("All sample tests passed.")
    print(result["counts_by_type"])
    print(result["key_definitions"])


if __name__ == "__main__":
    main()
