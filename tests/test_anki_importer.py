from __future__ import annotations

import unittest

from config.models import AnkiConfig, AnkiFieldConfig
from input.anki import AnkiImporter


class FakeClient:
    def deck_names(self):
        return ["Core 2K", "Mining"]

    def find_cards(self, query):
        if 'Core 2K' in query:
            return [1]
        if 'Mining' in query:
            return [2, 3]
        return []

    def cards_info(self, card_ids):
        cards = {
            1: {
                "cardId": 1,
                "note": 101,
                "deckName": "Core 2K",
                "fields": {
                    "Word": {"value": "教科書"},
                    "Word Reading": {"value": "きょうかしょ"},
                    "Word Meaning": {"value": "textbook"},
                    "Pitch Accent": {"value": "LHHH"},
                    "Frequency": {"value": "1,824"},
                },
                "reps": 20,
                "interval": 50,
                "lapses": 1,
                "factor": 2400,
                "queue": 2,
                "type": 2,
            },
            2: {
                "cardId": 2,
                "note": 202,
                "deckName": "Mining",
                "fields": {
                    "Word": {"value": "教科書"},
                    "Word Reading": {"value": "きょうかしょ"},
                    "Word Meaning": {"value": "textbook"},
                    "Pitch Accent": {"value": ""},
                    "Frequency": {"value": ""},
                },
                "reps": 10,
                "interval": 80,
                "lapses": 0,
                "factor": 2500,
                "queue": 2,
                "type": 2,
            },
            3: {
                "cardId": 3,
                "note": 303,
                "deckName": "Mining",
                "fields": {
                    "Word": {"value": "猫"},
                    "Word Reading": {"value": "ねこ"},
                    "Word Meaning": {"value": "cat"},
                    "Pitch Accent": {"value": "HL"},
                    "Frequency": {"value": "500"},
                },
                "reps": 5,
                "interval": 12,
                "lapses": 0,
                "factor": 2300,
                "queue": 2,
                "type": 2,
            },
        }
        return [cards[card_id] for card_id in card_ids]
    def get_reviews_of_cards(self, card_ids):
        histories = {
            "1": [[1704067200000, 1]],
            "2": [[1711929600000, 2]],
            "3": [[1714521600000, 3]],
        }
        return {str(card_id): histories.get(str(card_id), []) for card_id in card_ids}



class AnkiImporterTests(unittest.TestCase):
    def test_merges_duplicate_words_across_decks(self):
        config = AnkiConfig(
            decks=("Core 2K", "Mining"),
            fields=AnkiFieldConfig(),
        )
        result = AnkiImporter(config, client=FakeClient()).import_data()
        self.assertEqual(result["note_count"], 2)
        textbook = next(item for item in result["notes"] if item["word"] == "教科書")
        self.assertEqual(textbook["decks"], ["Core 2K", "Mining"])
        self.assertEqual(textbook["frequency"], 1824)
        self.assertEqual(textbook["study"]["reviews"], 30)
        self.assertEqual(textbook["study"]["best_interval"], 80)
        self.assertEqual(textbook["study"]["lapses"], 1)
        self.assertEqual(textbook["study"]["ease"], 2.5)
        self.assertEqual(textbook["study"]["last_reviewed"], "2024-04-01")


if __name__ == "__main__":
    unittest.main()



class MultiStructureClient(FakeClient):
    def deck_names(self):
        return ["Core 2K", "Japanese verbs (N5 - N4)"]

    def find_cards(self, query):
        if 'Core 2K' in query:
            return [1]
        if 'Japanese verbs (N5 - N4)' in query:
            return [10, 11]
        return []

    def cards_info(self, card_ids):
        base = {
            1: super().cards_info([1])[0],
            10: {
                "cardId": 10,
                "note": 1001,
                "deckName": "Japanese verbs (N5 - N4)",
                "fields": {
                    "word phrase sentence": {"value": "N + を + 食[た]べる"},
                    "word phrase sentence romaji": {"value": "N + o + taberu"},
                    "definition translation": {"value": "to eat"},
                },
                "reps": 8,
                "interval": 45,
                "lapses": 0,
                "factor": 2500,
                "queue": 2,
                "type": 2,
            },
            11: {
                "cardId": 11,
                "note": 1002,
                "deckName": "Japanese verbs (N5 - N4)",
                "fields": {
                    "word phrase sentence": {"value": "N + を + 修理[しゅうり]する<br>N + を + 直[なお]す"},
                    "word phrase sentence romaji": {"value": "N + o + shuri-suru<br>N + o + naosu"},
                    "definition translation": {"value": "to fix, repair"},
                },
                "reps": 4,
                "interval": 20,
                "lapses": 0,
                "factor": 2400,
                "queue": 2,
                "type": 2,
            },
        }
        return [base[card_id] for card_id in card_ids]

    def get_reviews_of_cards(self, card_ids):
        return {str(card_id): [] for card_id in card_ids}


def test_supports_per_deck_fields_and_furigana_lines():
    config = AnkiConfig(
        decks=("Core 2K", "Japanese verbs (N5 - N4)"),
        fields=AnkiFieldConfig(),
        deck_fields={
            "Japanese verbs (N5 - N4)": AnkiFieldConfig(
                word="word phrase sentence",
                reading="",
                meaning="definition translation",
                pitch_accent="",
                frequency="",
                furigana_in_word=True,
                split_lines=True,
            )
        },
    )
    result = AnkiImporter(config, client=MultiStructureClient()).import_data()

    by_word = {item["word"]: item for item in result["notes"]}
    assert "N + を + 食べる" in by_word
    assert by_word["N + を + 食べる"]["reading"] == "N + を + たべる"
    assert "N + を + 修理する" in by_word
    assert by_word["N + を + 修理する"]["reading"] == "N + を + しゅうりする"
    assert "N + を + 直す" in by_word
    assert by_word["N + を + 直す"]["reading"] == "N + を + なおす"
