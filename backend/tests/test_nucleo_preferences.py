import unittest

from fastapi import HTTPException

from app.services.nucleo_prefs import sanitize_preferences, schema_gap


class NucleoPreferencesTests(unittest.TestCase):
    def test_sanitize_keeps_theme_rules_and_drops_unknown_kinds(self) -> None:
        clean = sanitize_preferences(
            {
                "theme": "nucleo-claro",
                "fontScale": 1.3,
                "volume": 2,
                "alertRules": [
                    {
                        "id": "rule-1",
                        "kind": "sender",
                        "value": "netflix.com",
                        "enabled": True,
                    },
                    {"id": "bad", "kind": "balance", "value": "x"},
                ],
                "extra": "ignored",
            }
        )
        self.assertEqual(clean["theme"], "nucleo-claro")
        self.assertEqual(clean["fontScale"], 1.25)
        self.assertEqual(clean["volume"], 1.0)
        self.assertEqual(len(clean["alertRules"]), 1)
        self.assertNotIn("extra", clean)

    def test_top10_seen_flag_is_kept(self) -> None:
        clean = sanitize_preferences({"top10SeenAt": "2026-10-02T22:00:00.000Z"})
        self.assertEqual(clean["top10SeenAt"], "2026-10-02T22:00:00.000Z")
        self.assertIsNone(sanitize_preferences({"top10SeenAt": 5})["top10SeenAt"])
        self.assertIsNone(sanitize_preferences({})["top10SeenAt"])

    def test_unknown_theme_falls_back_to_nucleo(self) -> None:
        clean = sanitize_preferences({"theme": "midnight"})
        self.assertEqual(clean["theme"], "nucleo")

    def test_non_object_is_rejected(self) -> None:
        with self.assertRaises(HTTPException):
            sanitize_preferences(["nope"])

    def test_schema_gap_detects_missing_table(self) -> None:
        self.assertTrue(schema_gap(RuntimeError("42P01 relation does not exist")))
        self.assertFalse(schema_gap(RuntimeError("timeout")))


if __name__ == "__main__":
    unittest.main()
