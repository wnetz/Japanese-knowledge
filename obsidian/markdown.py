from __future__ import annotations

import re
from typing import Any

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
PROPERTY_RE = re.compile(r"^#([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
RUBY_RE = re.compile(r"\{([^|{}]+)(?:\|[^{}]+)+\}")
INLINE_TAG_RE = re.compile(r"(?<![\w/])#([A-Za-z0-9_\-/\u3040-\u30ff\u3400-\u9fff]+)")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)


def strip_ruby(text: str) -> str:
    """Keep the displayed word and discard Obsidian-only reading markup."""
    return RUBY_RE.sub(lambda match: match.group(1), text)


def extract_wikilinks(text: str) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for raw in WIKILINK_RE.findall(text):
        target, *alias = raw.split("|", 1)
        item = (strip_ruby(target.strip()), strip_ruby(alias[0].strip()) if alias else "")
        if item[0] and item not in seen:
            seen.add(item)
            result.append({"target": item[0], "alias": item[1]})
    return result


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    data: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in match.group(1).splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        list_match = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if list_match and current_list_key:
            data.setdefault(current_list_key, []).append(list_match.group(1).strip().strip("'\""))
            continue

        key_value = re.match(r"^([A-Za-z0-9_-]+):\s*(.*?)\s*$", line)
        if not key_value:
            current_list_key = None
            continue

        key, value = key_value.groups()
        if value == "":
            data[key] = []
            current_list_key = key
        elif value.startswith("[") and value.endswith("]"):
            data[key] = [part.strip().strip("'\"") for part in value[1:-1].split(",") if part.strip()]
            current_list_key = None
        elif value.lower() in {"true", "false"}:
            data[key] = value.lower() == "true"
            current_list_key = None
        else:
            data[key] = value.strip().strip("'\"")
            current_list_key = None

    return data, text[match.end():]


def extract_tags(text: str, frontmatter: dict[str, Any]) -> list[str]:
    tags: set[str] = set()
    fm_tags = frontmatter.get("tags", [])
    if isinstance(fm_tags, str):
        fm_tags = fm_tags.replace(",", " ").split()
    if isinstance(fm_tags, list):
        tags.update(str(tag).strip().lstrip("#") for tag in fm_tags if str(tag).strip())

    without_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    excluded = {"q", "a", "present", "present_negative", "past", "past_negative"}
    tags.update(tag for tag in INLINE_TAG_RE.findall(without_code) if tag not in excluded)
    return sorted(tags)


def parse_sections(body: str) -> list[dict[str, Any]]:
    """Return structural sections only; raw heading and section text are not retained."""
    sections: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    current: dict[str, Any] | None = {
        "level": 0,
        "heading": "",
        "heading_path": [],
        "_lines": [],
    }

    def finish() -> None:
        nonlocal current
        if current is not None:
            lines = current.pop("_lines")
            if current["heading"] or any(line.strip() for line in lines):
                current["lines"] = lines
                sections.append(current)
            current = None

    for line in body.splitlines():
        match = HEADING_RE.match(line)
        if not match:
            if current is not None:
                current["_lines"].append(line)
            continue

        level = len(match.group(1))
        heading_raw = match.group(2).strip()
        if level == 1 and re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:", heading_raw):
            if current is not None:
                current["_lines"].append(line)
            continue

        finish()
        stack = [item for item in stack if item["level"] < level]
        heading = strip_ruby(heading_raw)
        current = {
            "level": level,
            "heading": heading,
            "heading_path": [item["heading"] for item in stack] + [heading],
            "_lines": [],
        }
        stack.append({"level": level, "heading": heading})

    finish()
    return sections
