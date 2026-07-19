from pathlib import Path

from importers.obsidian import ObsidianParser


def test_parses_compact_verb_form_and_conjugation_profile(tmp_path: Path) -> None:
    (tmp_path / "辞書形.md").write_text(
        """---
note_type: verb form
---
# V3
- する
- くる
# V2:
- 一段動詞
- /い/ or /え/ + る
# V1
- 五段動詞
- /う/
- not V3 or V2
""",
        encoding="utf-8",
    )
    (tmp_path / "たい形動詞.md").write_text(
        """---
note_type: conjugation
name: たい形
---
# conjugation
#non_past:たい
#non_past_negative :たくない
#past :たかった
#past_negative :たくなかった
# [[辞書形#V1]]
辞書形(/う/ ->/い/ ) + conjugation
# [[辞書形#V2]]
辞書形 - る + conjugation
# # [[辞書形#V3]]
する -> し + conjugation
くる -> き + conjugation
""",
        encoding="utf-8",
    )

    parser = ObsidianParser(tmp_path)
    parser.scan()
    result = parser.export()

    assert set(result) == {
        "key_definitions", "conjugations", "verb_forms", "groups", "lessons"
    }
    assert result["conjugations"] == [{
        "name": "たい形",
        "forms": {
            "non_past": "たい",
            "non_past_negative": "たくない",
            "past": "たかった",
            "past_negative": "たくなかった",
        },
        "transformations": {
            "V1": ["辞書形(/う/ ->/い/ ) + conjugation"],
            "V2": ["辞書形 - る + conjugation"],
            "V3": ["する -> し + conjugation", "くる -> き + conjugation"],
        },
    }]
    assert result["verb_forms"] == [{
        "V3": ["する", "くる"],
        "V2": ["一段動詞", "/い/ or /え/ + る"],
        "V1": ["五段動詞", "/う/", "not V3 or V2"],
    }]
