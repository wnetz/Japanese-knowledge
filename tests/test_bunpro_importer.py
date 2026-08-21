from __future__ import annotations

from input.bunpro import BunproImporter


class FakeBunproClient:
    SRS_LEVELS = ("beginner", "adept", "seasoned", "expert", "master")

    def get_user(self):
        return {
            "user": {
                "data": {
                    "id": "9",
                    "attributes": {
                        "id": 9,
                        "username": "William",
                        "level": 7,
                        "xp": 1234,
                        "language": "en",
                        "vacation_mode": False,
                    },
                }
            }
        }

    def get_srs_overview(self):
        return {"grammar": {"beginner": 1}, "vocab": {"beginner": 1}}

    def get_jlpt_progress(self):
        return {"grammar": {"N5": {"beginner": 1, "total_count": 100}}, "vocab": {}}

    def get_srs_level_details(self, level, reviewable_type, *, page=1):
        if level != "beginner":
            return {"reviews": {"data": [], "included": []}, "pagy": {"page": 1, "pages": 1, "next": None}}

        if reviewable_type == "GrammarPoint":
            return {
                "reviews": {
                    "data": [{
                        "id": "501",
                        "type": "review",
                        "attributes": {
                            "reviewable_id": 101,
                            "reviewable_type": "GrammarPoint",
                            "streak": 3,
                            "accuracy": 91,
                            "times_studied": 8,
                            "complete": False,
                        },
                    }],
                    "included": [{
                        "id": "101",
                        "type": "grammar_point",
                        "attributes": {
                            "id": 101,
                            "slug": "to-omou",
                            "title": "～と思う",
                            "meaning": "I think that",
                            "level": "N4",
                        },
                    }],
                },
                "pagy": {"page": 1, "pages": 1, "next": None},
            }

        return {
            "reviews": {
                "data": [{
                    "id": "601",
                    "type": "review",
                    "attributes": {
                        "reviewable_id": 201,
                        "reviewable_type": "Vocab",
                        "streak": 2,
                        "accuracy": 88,
                        "times_studied": 5,
                    },
                }],
                "included": [{
                    "id": "201",
                    "type": "vocab",
                    "attributes": {
                        "id": 201,
                        "slug": "食べる",
                        "title": "食べる",
                        "meaning": "to eat",
                        "level": "N5",
                    },
                }],
            },
            "pagy": {"page": 1, "pages": 1, "next": None},
        }


def test_bunpro_importer_builds_compact_knowledge_index():
    importer = BunproImporter("unused", "unused", client=FakeBunproClient())
    result = importer.import_data()

    assert result["source"] == "bunpro"
    assert result["api"] == "unofficial_frontend"
    assert result["user"]["username"] == "William"
    assert result["counts"] == {"grammar": 1, "vocabulary": 1}
    assert result["grammar"] == [{
        "id": 101,
        "slug": "to-omou",
        "title": "～と思う",
        "meaning": "I think that",
        "level": "N4",
        "study": {
            "srs_level": "beginner",
            "streak": 3,
            "accuracy": 91,
            "times_studied": 8,
            "complete": False,
        },
    }]
    assert result["vocabulary"][0]["title"] == "食べる"
    assert result["vocabulary"][0]["study"]["srs_level"] == "beginner"
