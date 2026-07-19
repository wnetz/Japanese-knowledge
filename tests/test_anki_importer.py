from __future__ import annotations

import unittest

from config.models import AnkiConfig, AnkiFieldConfig
from importers.anki import AnkiImporter


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
            enabled=True,
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
