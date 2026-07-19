from pathlib import Path

from importers.obsidian import ObsidianParser


def test_group_export_removes_parser_metadata_and_duplicate_pos_name(tmp_path: Path) -> None:
    (tmp_path / "かぎ.md").write_text(
        """---
note_type: key
---
# placeholders
#☆: 形容詞
""",
        encoding="utf-8",
    )
    (tmp_path / "色.md").write_text(
        """---
note_type: group
name: 色
---
# 4 basic colors
- 赤い :: #☆
# Notes
赤い is an adjective.
""",
        encoding="utf-8",
    )

    parser = ObsidianParser(tmp_path)
    parser.scan()
    result = parser.export()

    assert result["groups"] == [{
        "name": "色",
        "groups": [{
            "name": "4 basic colors",
            "members": [{"word": "赤い", "part_of_speech": "#☆"}],
        }],
        "notes": ["赤い is an adjective."],
    }]

    serialized = str(result)
    for removed in (
        "schema_version", "vault", "knowledge_engine_folder", "note_count",
        "counts_by_type", "frontmatter", "filename", "folder", "path",
        "title", "tags", "wikilinks", "note_type", "part_of_speech_name",
        "placeholders", "type", "value",
    ):
        assert removed not in serialized
