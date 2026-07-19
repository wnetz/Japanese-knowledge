from __future__ import annotations

import unittest

from wanikani.importer import WaniKaniImporter
from wanikani.normalization import normalize_parts_of_speech


class FakeClient:
    REVISION = "20170710"

    def get(self, endpoint, params=None):
        if endpoint == "user":
            return {"data": {"username": "William", "level": 3}}
        raise AssertionError(endpoint)

    def iter_collection(self, endpoint, params=None):
        if endpoint == "subjects":
            yield {
                "id": 101,
                "object": "vocabulary",
                "data_updated_at": "2026-07-17T00:00:00Z",
                "data": {
                    "level": 2,
                    "characters": "勉強する",
                    "slug": "勉強する",
                    "meanings": [{"meaning": "To Study", "primary": True, "accepted_answer": True}],
                    "readings": [{"reading": "べんきょうする", "primary": True, "accepted_answer": True}],
                    "parts_of_speech": ["noun", "suru_verb", "transitive_verb"],
                    "component_subject_ids": [1, 2],
                    "context_sentences": [{"ja": "日本語を勉強する。", "en": "I study Japanese."}],
                },
            }
        elif endpoint == "assignments":
            yield {"id": 201, "data": {"subject_id": 101, "srs_stage": 4}}
        elif endpoint == "review_statistics":
            yield {"id": 301, "data": {"subject_id": 101, "percentage_correct": 92}}
        else:
            raise AssertionError(endpoint)


class WaniKaniImporterTests(unittest.TestCase):
    def test_pos_normalization(self):
        result = normalize_parts_of_speech(["noun", "suru verb", "transitive_verb"])
        self.assertIn("noun", result["categories"])
        self.assertIn("verb", result["categories"])
        self.assertIn("suru_verb", result["normalized"])

    def test_importer_merges_progress(self):
        importer = WaniKaniImporter("unused", client=FakeClient())
        result = importer.import_all()
        subject = result["subjects"][0]
        self.assertEqual(subject["characters"], "勉強する")
        self.assertEqual(subject["assignment"]["srs_stage"], 4)
        self.assertEqual(subject["review_statistics"]["percentage_correct"], 92)
        self.assertIn("verb", subject["parts_of_speech"]["categories"])


if __name__ == "__main__":
    unittest.main()
