from pathlib import Path

from importers.obsidian import ObsidianParser


def test_lesson_sections_are_merged_classified_and_exported_as_strings(tmp_path: Path) -> None:
    note = tmp_path / "第２章.md"
    note.write_text(
        """---
note_type: lesson
---
# 2-1
## Can Do
- 買いたいものを店員に言うことができる。
## 宿題
- ０から999,999発音
- #q いくつですか
- #a 「つ」助数詞１から１０
- #○○ を #△ つください
## 教科書
- #q いくらですか
- #a #△ 円です
- #○○ (を) ください
""",
        encoding="utf-8",
    )

    parser = ObsidianParser(tmp_path)
    parser.scan()
    result = parser.export()
    lesson = result["lessons"][0]

    assert lesson == {
        "id": "2-1",
        "can_do": ["買いたいものを店員に言うことができる。"],
        "practice": {
            "skills": ["０から999,999発音"],
            "questions": ["いくつですか", "いくらですか"],
            "responses": ["「つ」助数詞１から１０", "#△ 円です"],
            "patterns": ["#○○ を #△ つください", "#○○ (を) ください"],
        },
    }
