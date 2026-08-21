# Japanese Knowledge Engine

This project builds Japanese-learning profiles from several independent input sources and local/manual data.

## Project layout

```text
input/
  anki/
  bunpro/
  obsidian/
  wanikani/

config/
core/
goals/
grammar/
history/
profile/
writing/
gui/

output/
  auto/      # generated or refreshable data
  manual/    # local/user-authored data
  knowledge_profile.json
```

All source adapters live under `input/`. There are no duplicate top-level Anki,
WaniKani, or Obsidian importer packages.

## Updating profiles

Run the GUI and choose which external services to refresh, or use:

```bash
python update_profile.py --sources anki,wanikani,bunpro
```

The GUI/`--sources` argument is the source-selection mechanism. `config.json`
does not contain separate `enabled` switches.

If a source is not selected, its existing index is preserved and the derived
profiles are rebuilt from the data already on disk.

Obsidian is local project input rather than an external refresh choice, so it is
refreshed on every profile rebuild.

## Configuration

`config.json` contains source connection/import settings and output paths.
Secrets belong in `config.local.json`, which overrides `config.json` and is
ignored by Git.

For example, Bunpro credentials can be stored locally as:

```json
{
  "bunpro": {
    "email": "YOUR_BUNPRO_EMAIL",
    "password": "YOUR_BUNPRO_PASSWORD"
  }
}
```

WaniKani API credentials should likewise be kept in `config.local.json`.

## Output responsibilities

- `output/auto/wanikani_index.json` — WaniKani source index
- `output/auto/anki_index.json` — Anki source index
- `output/auto/grammar_profile.json` — Bunpro grammar/vocabulary study data
- `output/auto/textbook_profile.json` — Obsidian textbook/lesson knowledge
- `output/auto/vocabulary_profile.json` — merged vocabulary profile
- `output/manual/` — irreplaceable/local data such as writing history, goals,
  Migaku-known words, grammar mastery, and SRS history
- `output/knowledge_profile.json` — combined knowledge profile

The vocabulary profile merges WaniKani, Anki, and optional
`output/manual/migaku_known_words.json`. Obsidian textbook information remains
separate from vocabulary source scoring.

## Input source notes

### Bunpro

The Bunpro adapter uses the unofficial frontend API used by the Bunpro website.
It is read-only and intentionally isolated under `input/bunpro/`.

### Obsidian

The Obsidian parser is under `input/obsidian/`. Parser-format notes are in
`docs/OBSIDIAN_PARSER.md`.

### Anki

See `ANKI_SETUP.md` for deck and field configuration.
