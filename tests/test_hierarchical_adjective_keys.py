from importers.obsidian.base import BaseNoteParser
from importers.obsidian.key import KeyParser
from pathlib import Path


def test_key_parser_accepts_hierarchical_adjective_symbols():
    body = """# Any adjective: #☆\n# い adjective: #☆/い\n# な adjective: #☆/な\n"""
    note = KeyParser().parse(
        path=Path("Knowledge Engine/adjective keys.md"),
        raw_text=body,
        body=body,
        frontmatter={"note_type": "key"},
    )
    assert note.definitions == {
        "#☆": "Any adjective",
        "#☆/い": "い adjective",
        "#☆/な": "な adjective",
    }


def test_specific_adjective_key_does_not_also_match_parent():
    parser = BaseNoteParser({
        "#☆": "Any adjective",
        "#☆/い": "い adjective",
        "#☆/な": "な adjective",
    })
    assert parser.extract_placeholders("#☆/い + noun") == ["#☆/い"]
    assert parser.extract_placeholders("#☆/な + noun") == ["#☆/な"]
    assert parser.extract_placeholders("#☆ + noun") == ["#☆"]


def test_multiple_adjective_keys_keep_reading_order():
    parser = BaseNoteParser({
        "#☆": "Any adjective",
        "#☆/い": "い adjective",
        "#☆/な": "な adjective",
    })
    assert parser.extract_placeholders("#☆/な or #☆/い or #☆") == [
        "#☆/な", "#☆/い", "#☆"
    ]


def test_hierarchical_keys_work_without_loaded_key_file():
    parser = BaseNoteParser()
    assert parser.extract_placeholders("#☆/い") == ["#☆/い"]
    assert parser.extract_placeholders("#☆/な") == ["#☆/な"]
