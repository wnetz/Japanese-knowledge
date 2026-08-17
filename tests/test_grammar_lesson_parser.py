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



def test_keigo_arrow_lines_export_as_transformations_not_patterns(tmp_path: Path) -> None:
    (tmp_path / "かぎ.md").write_text(
        """---
note_type: key
---
# placeholders
#→尊敬語: 尊敬語
#→謙譲語: 謙譲語
""",
        encoding="utf-8",
    )
    (tmp_path / "第１６章.md").write_text(
        """---
note_type: lesson
---
# 16-1
## Can Do
- 敬語を使って目上の人と簡単な話ができる。
## 教科書
- 行きます #→尊敬語 いらっしゃいます
- 言います #→尊敬語 おっしゃいます
- （もし) #～ たら、 #∵
# 16-3
## 教科書
- 行きます #→謙譲語 まいります
- 言います #→謙譲語 もうします
""",
        encoding="utf-8",
    )

    parser = ObsidianParser(tmp_path)
    parser.scan()
    result = parser.export()

    assert result["lessons"][0]["practice"] == {
        "patterns": ["（もし) #～ たら、 #∵"],
        "transformations": [
            {"form": "行きます", "to": "いらっしゃいます", "by": "尊敬語"},
            {"form": "言います", "to": "おっしゃいます", "by": "尊敬語"},
        ],
    }
    assert result["lessons"][1]["practice"] == {
        "transformations": [
            {"form": "行きます", "to": "まいります", "by": "謙譲語"},
            {"form": "言います", "to": "もうします", "by": "謙譲語"},
        ],
    }
