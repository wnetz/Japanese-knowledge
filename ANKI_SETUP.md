# Anki stage setup

The Anki importer uses the local AnkiConnect add-on. Anki must be open while
`update_profile.py` runs.

## Configuration

Add the exact deck names to `config.local.json` (recommended) or `config.json`:

```json
{
  "anki": {
    "enabled": true,
    "host": "http://localhost:8765",
    "decks": [
      "Your first deck",
      "Your second deck"
    ]
  }
}
```

The default field mapping matches the shared note type:

```json
{
  "anki": {
    "fields": {
      "word": "Word",
      "reading": "Word Reading",
      "meaning": "Word Meaning",
      "pitch_accent": "Pitch Accent",
      "frequency": "Frequency"
    }
  }
}
```

## Output

The importer writes `output/anki_index.json`. It keeps only:

- word
- reading
- meaning
- pitch accent
- frequency
- deck membership
- reviews, best interval, lapses, ease, state, and last-reviewed date

Entries are merged using the `Word` field alone. Duplicate deck names are
removed, reviews and lapses are summed, and the highest interval and ease are
kept. Conflicting non-empty readings or meanings are reported in the output's
`errors` array.
