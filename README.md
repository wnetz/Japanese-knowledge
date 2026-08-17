# Japanese Knowledge Engine

This project maintains separate data artifacts for different responsibilities.

## Vocabulary profile

`update_profile.py` refreshes the enabled source importers. WaniKani and Anki are
then merged into:

```text
output/vocabulary_profile.json
```

The vocabulary profile contains merged vocabulary, source-specific study data,
and a confidence score estimating William's familiarity with each word.
Obsidian is deliberately not included in this profile.


## Bunpro

Bunpro can be imported as a separate study-knowledge artifact:

```text
output/grammar_profile.json
```

The importer uses the same **unofficial frontend API** used by the Bunpro
website. Bunpro has explicitly noted that this API may change without notice, so
the importer is isolated from the rest of the profile pipeline. It is read-only.

Enable Bunpro in `config.json` (or override it in `config.local.json`):

```json
{
  "bunpro": {
    "enabled": true,
    "email": "YOUR_BUNPRO_EMAIL",
    "password": "YOUR_BUNPRO_PASSWORD"
  }
}
```

Credentials should be stored in `config.local.json`, which is ignored by Git.
They are used only to obtain Bunpro's `frontend_api_token` and are never written
to the generated index.

The index currently collects every studied grammar point and vocabulary item in
Bunpro's standard SRS stages (`beginner`, `adept`, `seasoned`, `expert`,
`master`), including the item's Bunpro ID/title/meaning/JLPT level and compact
study state such as SRS level, streak, accuracy, review count, and next review.
Bunpro data is intentionally kept separate from `textbook_profile.json`.

## Obsidian

The Obsidian importer remains available as an independent component and can
continue producing:

```text
output/textbook_profile.json
```

Alex can load `vocabulary_profile.json` and `textbook_profile.json` separately
when it needs both vocabulary and grammar or lesson information.

## Run

```bash
python update_profile.py
```

Enabled importers are controlled by `config.json` or `config.local.json`.
Existing WaniKani or Anki index files can still be used when their importer is
disabled.

## Migaku vocabulary

If the Migaku Words extension export is saved as:

```text
output/migaku_known_words.json
```

the vocabulary profile builder automatically merges it with WaniKani and Anki.
Migaku `KNOWN` words are included as vocabulary knowledge and contribute a
strong confidence signal. Reading identity is normalized between katakana and
hiragana so equivalent readings merge without collapsing genuinely different
readings.


### Compact profile output

`output/vocabulary_profile.json` keeps only teaching-relevant fields. Anki study
data is serialized as `reviews`, `ease`, and `last_reviewed`; WaniKani study data
is serialized as `srs_stage`. Pitch accent, frequency, WaniKani milestone dates,
and other raw scoring inputs are not copied into the final profile.
