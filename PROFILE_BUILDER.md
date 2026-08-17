# Vocabulary Profile Builder

`ProfileBuilder` has one responsibility: merge the WaniKani and Anki vocabulary
indexes and calculate familiarity confidence.

It reads any available files named:

- `output/wanikani_index.json`
- `output/anki_index.json`

It writes:

- `output/vocabulary_profile.json`

`textbook_profile.json` is intentionally ignored, even when it exists in the same
output directory.

## Use from the command line

```bash
python update_profile.py
```

## Use from Python

```python
from profile import ProfileBuilder

builder = ProfileBuilder("output")
profile = builder.build_and_write()
print(builder.statistics.format())
```

Do not run `profile/builder.py` directly. It is a package module.

## Vocabulary identity

Vocabulary is merged by `(word, reading)`. Matching WaniKani and Anki entries
become one vocabulary item whose `sources` list contains both source names.

## Confidence

Confidence estimates William's familiarity with a word.

- WaniKani has a 70% weight.
- Anki has a 30% weight.
- Weights are renormalized over studied platforms only.
- A word present but unstudied on a platform is ignored rather than penalized.
- A word with no study evidence has `confidence: null`.

The formulas are isolated in `profile/scoring.py`.

## Final vocabulary JSON

The final `vocabulary_profile.json` is intentionally compact. Source indexes may
retain richer import data, but each profile entry exposes only information useful
to Alex:

```json
{
  "word": "食べる",
  "reading": "たべる",
  "meanings": ["To Eat", "eat"],
  "parts_of_speech": ["ichidan verb"],
  "sources": ["anki", "wanikani"],
  "confidence": 0.91,
  "study": {
    "anki": {
      "reviews": 37,
      "ease": 2.45,
      "last_reviewed": "2026-07-14"
    },
    "wanikani": {
      "srs_stage": 7
    }
  }
}
```

The final profile does not include pitch accent, frequency, WaniKani milestone
timestamps, raw answer totals, Anki intervals/lapses/state, source IDs, or a
schema version. Those values can remain in the source indexes when needed for
rebuilding and confidence calculation.
