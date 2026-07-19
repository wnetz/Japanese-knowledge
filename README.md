# Japanese Knowledge Engine

This project maintains separate data artifacts for different responsibilities.

## Vocabulary profile

`update_profile.py` refreshes the enabled WaniKani and Anki sources, then merges
those two indexes into:

```text
output/vocabulary_profile.json
```

The vocabulary profile contains merged vocabulary, source-specific study data,
and a confidence score estimating William's familiarity with each word.
Obsidian is deliberately not included in this profile.

## Obsidian

The Obsidian importer remains available as an independent component and can
continue producing:

```text
output/grammar_profile.json
```

Alex can load `vocabulary_profile.json` and `grammar_profile.json` separately
when it needs both vocabulary and grammar or lesson information.

## Run

```bash
python update_profile.py
```

Enabled importers are controlled by `config.json` or `config.local.json`.
Existing WaniKani or Anki index files can still be used when their importer is
disabled.

### Compact profile output

`output/vocabulary_profile.json` keeps only teaching-relevant fields. Anki study
data is serialized as `reviews`, `ease`, and `last_reviewed`; WaniKani study data
is serialized as `srs_stage`. Pitch accent, frequency, WaniKani milestone dates,
and other raw scoring inputs are not copied into the final profile.
