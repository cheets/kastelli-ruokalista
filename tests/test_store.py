import json
import tempfile
import unittest
from pathlib import Path

from kastelli_menu.parser import Section
from kastelli_menu.store import load, merge, save

DAY_A = {"2026-08-17": [Section("Lounas", ["Nakkikastike, perunat"])]}
DAY_B = {"2026-08-24": [Section("Lounas", ["Keitto"])]}


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()) / "menus.json"

    def test_load_missing_file_returns_empty_archive(self):
        days, updated = load(self.tmp)
        self.assertEqual(days, {})
        self.assertIsNone(updated)

    def test_roundtrip_preserves_sections(self):
        save(self.tmp, DAY_A, updated="2026-08-20T04:00:00Z")
        days, updated = load(self.tmp)
        self.assertEqual(days, DAY_A)
        self.assertEqual(updated, "2026-08-20T04:00:00Z")

    def test_merge_adds_new_weeks(self):
        merged, changed = merge(dict(DAY_A), DAY_B, today="2026-08-24")
        self.assertTrue(changed)
        self.assertEqual(sorted(merged), ["2026-08-17", "2026-08-24"])

    def test_merge_reports_no_change_for_identical_data(self):
        merged, changed = merge(dict(DAY_A), DAY_A, today="2026-08-17")
        self.assertFalse(changed)
        self.assertEqual(merged, DAY_A)

    def test_merge_overwrites_a_corrected_day(self):
        fixed = {"2026-08-17": [Section("Lounas", ["Kalakeitto"])]}
        merged, changed = merge(dict(DAY_A), fixed, today="2026-08-17")
        self.assertTrue(changed)
        self.assertEqual(merged["2026-08-17"][0].items, ["Kalakeitto"])

    def test_merge_never_deletes_a_day_missing_from_the_scrape(self):
        merged, _ = merge(dict(DAY_A), {}, today="2026-08-17")
        self.assertIn("2026-08-17", merged)

    def test_merge_prunes_days_older_than_the_retention_window(self):
        old = {"2020-01-06": [Section("Lounas", ["Muinaisruoka"])]}
        merged, changed = merge({**DAY_A, **old}, {}, today="2026-08-17")
        self.assertTrue(changed)
        self.assertNotIn("2020-01-06", merged)

    def test_saved_json_is_human_readable_and_stable(self):
        save(self.tmp, DAY_A, updated="2026-08-20T04:00:00Z")
        raw = json.loads(self.tmp.read_text(encoding="utf-8"))
        self.assertEqual(raw["days"]["2026-08-17"][0]["name"], "Lounas")
        self.assertIn("Nakkikastike", self.tmp.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
