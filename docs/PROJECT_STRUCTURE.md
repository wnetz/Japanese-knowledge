# Project Structure

## Source adapters

All data-source integrations live under `input/`:

- `input/anki/`
- `input/wanikani/`
- `input/bunpro/`
- `input/obsidian/`

`update_profile.py` is the orchestration entry point. External refresh selection is
provided by the GUI or `--sources`; source adapters do not have independent
`enabled` config switches.

Obsidian is a local project source and is refreshed during every profile rebuild.

## Core domains

- `config/` — configuration models/loading
- `core/` — shared serialization/knowledge models
- `profile/` — vocabulary/knowledge profile aggregation
- `writing/` — writing profile and SRS
- `grammar/` — grammar mastery history
- `goals/` — daily goal scheduling/history
- `history/` — SRS history and graph-series preparation
- `gui/` — application windows/screens

## Data

- `output/auto/` — generated or externally refreshable artifacts
- `output/manual/` — local/user-authored or difficult-to-recover data
- `output/knowledge_profile.json` — combined knowledge profile

## Entry points

- `japanese_knowledge_gui.py` — GUI
- `update_profile.py` — profile refresh/rebuild
- `python -m input.wanikani.cli` — standalone WaniKani import

## Local files

`.venv/`, `.git/`, Python caches, pytest caches, and `config.local.json` are not
part of a portable source archive. Keep credentials in `config.local.json`.
