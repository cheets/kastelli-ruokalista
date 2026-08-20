import pathlib
import unittest

from kastelli_menu.parser import Section, parse_week

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


class ParseWeekTest(unittest.TestCase):
    def setUp(self):
        self.week = parse_week(fixture("week34_full.html"))

    def test_returns_every_school_day(self):
        self.assertEqual(
            sorted(self.week),
            [
                "2026-08-17",
                "2026-08-18",
                "2026-08-19",
                "2026-08-20",
                "2026-08-21",
            ],
        )

    def test_sections_and_items_of_a_day(self):
        self.assertEqual(
            self.week["2026-08-20"],
            [
                Section("Lounas", ["Lohipastavuoka"]),
                Section("Kasvislounas", ["Juustoinen pastavuoka"]),
                Section("Lisäkkeet", ["Jäävuori-kurkku-hernesalaatti, punajuuri"]),
            ],
        )

    def test_decodes_html_entities(self):
        names = [section.name for section in self.week["2026-08-19"]]
        self.assertIn("Lisäkkeet", names)
        self.assertIn("Jälkiruoka", names)

    def test_normalizes_kasvisruoka_to_kasvislounas(self):
        # Mon uses "Kasvisruoka" in the source, Wed uses "Kasvislounas".
        for date in ("2026-08-17", "2026-08-19"):
            names = [section.name for section in self.week[date]]
            self.assertIn("Kasvislounas", names)
            self.assertNotIn("Kasvisruoka", names)

    def test_keeps_source_order_of_sections(self):
        self.assertEqual(
            [section.name for section in self.week["2026-08-19"]],
            ["Lounas", "Kasvislounas", "Lisäkkeet", "Jälkiruoka"],
        )

    def test_ignores_markup_outside_the_week_menu(self):
        # The nutrition popup after the menu contains an <h3> reading
        # "Ravintoarvot / 100 g"; it must not attach to the last day.
        friday = [section.name for section in self.week["2026-08-21"]]
        self.assertEqual(friday, ["Lounas", "Lisäkkeet"])

    def test_empty_week_yields_no_days(self):
        self.assertEqual(parse_week(fixture("week35_empty.html")), {})

    def test_unrelated_html_yields_no_days(self):
        self.assertEqual(parse_week("<html><body>hello</body></html>"), {})


if __name__ == "__main__":
    unittest.main()
