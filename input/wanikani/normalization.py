from __future__ import annotations

from collections.abc import Iterable

# WaniKani deliberately uses detailed labels.  We keep every original label and
# derive broader canonical categories for matching lesson placeholders.
POS_ALIASES: dict[str, str] = {
    "noun": "noun",
    "proper_noun": "proper_noun",
    "pronoun": "pronoun",
    "counter": "counter",
    "prefix": "prefix",
    "suffix": "suffix",
    "expression": "expression",
    "adverb": "adverb",
    "conjunction": "conjunction",
    "interjection": "interjection",
    "particle": "particle",
    "auxiliary_verb": "auxiliary_verb",
    "auxiliary_adjective": "auxiliary_adjective",
    "i_adjective": "i_adjective",
    "na_adjective": "na_adjective",
    "no_adjective": "no_adjective",
    "taru_adjective": "taru_adjective",
    "pre_noun_adjectival": "pre_noun_adjectival",
    "suru_verb": "suru_verb",
    "godan_verb": "godan_verb",
    "ichidan_verb": "ichidan_verb",
    "intransitive_verb": "intransitive_verb",
    "transitive_verb": "transitive_verb",
}

BROAD_CATEGORIES: dict[str, set[str]] = {
    "noun": {"noun", "proper_noun", "pronoun", "counter"},
    "verb": {
        "suru_verb",
        "godan_verb",
        "ichidan_verb",
        "intransitive_verb",
        "transitive_verb",
        "auxiliary_verb",
    },
    "adjective": {
        "i_adjective",
        "na_adjective",
        "no_adjective",
        "taru_adjective",
        "pre_noun_adjectival",
        "auxiliary_adjective",
    },
}

JAPANESE_DISPLAY: dict[str, str] = {
    "noun": "名詞",
    "proper_noun": "固有名詞",
    "pronoun": "代名詞",
    "counter": "助数詞",
    "verb": "動詞",
    "suru_verb": "する動詞",
    "godan_verb": "五段動詞",
    "ichidan_verb": "一段動詞",
    "intransitive_verb": "自動詞",
    "transitive_verb": "他動詞",
    "auxiliary_verb": "助動詞",
    "adjective": "形容詞",
    "i_adjective": "い形容詞",
    "na_adjective": "な形容詞",
    "no_adjective": "の形容詞",
    "adverb": "副詞",
    "conjunction": "接続詞",
    "interjection": "感動詞",
    "particle": "助詞",
    "prefix": "接頭辞",
    "suffix": "接尾辞",
    "expression": "表現",
}


def normalize_label(label: str) -> str:
    """Normalize API labels without destroying unknown future labels."""
    cleaned = label.strip().lower().replace("-", "_").replace(" ", "_")
    return POS_ALIASES.get(cleaned, cleaned)


def normalize_parts_of_speech(labels: Iterable[str]) -> dict[str, list[str]]:
    """Return exact labels, broad categories, and Japanese display labels."""
    exact = list(dict.fromkeys(normalize_label(label) for label in labels if label))

    broad: list[str] = []
    for category, members in BROAD_CATEGORIES.items():
        if any(label in members for label in exact):
            broad.append(category)

    # Exact labels can also be useful as matchable categories.
    categories = list(dict.fromkeys([*broad, *exact]))
    japanese = list(
        dict.fromkeys(
            JAPANESE_DISPLAY[label]
            for label in categories
            if label in JAPANESE_DISPLAY
        )
    )

    return {
        "raw": list(dict.fromkeys(label for label in labels if label)),
        "normalized": exact,
        "categories": categories,
        "japanese": japanese,
    }
