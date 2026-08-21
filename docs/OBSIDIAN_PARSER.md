# Obsidian Parser V2

V2 keeps the existing public entry point:

```python
from input.obsidian import ObsidianParser

parser = ObsidianParser("/path/to/vault")
parser.scan()
parser.save_json("profile.json")
```

## Main changes

- Ruby markup is stripped and is not exported.
- Raw Markdown, raw headings, raw lines, duplicated section text, and line numbers are not exported.
- Group members support `word :: placeholder` syntax.
- Group placeholders are resolved through key files.
- A `# notes` section is exported as notes rather than as a vocabulary group.
- Unheaded group lists are supported.
- Lesson information is stored once inside structured sections rather than duplicated into questions, answers, and patterns arrays.
- Empty optional fields are omitted from serialized notes.

## Group syntax

```markdown
---
note_type: group
name: 色
---
# 4 basic colors
- 赤い :: #☆
- 青い :: #☆

# everything else
- 緑色 :: #○○

# notes
Any explanatory notes go here.
```

A member becomes:

```json
{
  "word": "赤い",
  "part_of_speech": "#☆",
  "part_of_speech_name": "形容詞"
}
```

## Ruby behavior

```markdown
{紫|むらさき}色
```

is exported simply as:

```text
紫色
```
