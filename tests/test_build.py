import pathlib
import tempfile
import unittest
from datetime import date

from kastelli_menu.build import build, feed_window, monday_of, scrape
from kastelli_menu.parser import Section

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
WEEK34 = (FIXTURES / "week34_full.html").read_text(encoding="utf-8")
EMPTY = (FIXTURES / "week35_empty.html").read_text(encoding="utf-8")


def fake_fetcher(pages):
    calls = []

    def fetch(url):
        calls.append(url)
        return pages[len(calls) - 1]

    fetch.calls = calls
    return fetch


class MondayTest(unittest.TestCase):
    def test_monday_of_a_thursday(self):
        self.assertEqual(monday_of(date(2026, 8, 20)), date(2026, 8, 17))

    def test_monday_of_a_monday_is_itself(self):
        self.assertEqual(monday_of(date(2026, 8, 17)), date(2026, 8, 17))


class ScrapeTest(unittest.TestCase):
    def test_requests_this_week_and_next(self):
        fetch = fake_fetcher([WEEK34, EMPTY])
        scrape(date(2026, 8, 20), fetch)
        self.assertEqual(
            fetch.calls,
            [
                "https://ravintolapalvelut.iss.fi/kastelli/?date=2026-08-17",
                "https://ravintolapalvelut.iss.fi/kastelli/?date=2026-08-24",
            ],
        )

    def test_empty_next_week_is_not_a_warning(self):
        days, warnings = scrape(date(2026, 8, 20), fake_fetcher([WEEK34, EMPTY]))
        self.assertEqual(len(days), 5)
        self.assertEqual(warnings, [])

    def test_unrecognised_markup_raises_a_warning(self):
        _, warnings = scrape(date(2026, 8, 20), fake_fetcher(["<html>redesign</html>"] * 2))
        self.assertEqual(len(warnings), 2)
        self.assertIn("markup may have changed", warnings[0])


class FeedWindowTest(unittest.TestCase):
    def test_drops_days_older_than_two_weeks(self):
        days = {
            "2026-07-01": [Section("Lounas", ["Vanha"])],
            "2026-08-17": [Section("Lounas", ["Uusi"])],
        }
        self.assertEqual(list(feed_window(days, date(2026, 8, 20))), ["2026-08-17"])


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())

    def run_build(self, pages):
        return build(
            self.root / "data" / "menus.json",
            self.root / "docs",
            date(2026, 8, 20),
            fake_fetcher(pages),
        )

    def test_writes_both_feeds_and_the_archive(self):
        self.assertEqual(self.run_build([WEEK34, EMPTY]), 0)
        self.assertIn("to 20.8.2026", (self.root / "docs" / "menu.xml").read_text("utf-8"))
        self.assertIn("BEGIN:VCALENDAR", (self.root / "docs" / "menu.ics").read_text("utf-8"))
        self.assertTrue((self.root / "data" / "menus.json").exists())

    def test_written_ics_keeps_crlf_line_endings_on_disk(self):
        self.run_build([WEEK34, EMPTY])
        raw = (self.root / "docs" / "menu.ics").read_bytes()
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))
        self.assertNotIn(b"\r\r", raw)

    def test_second_identical_run_leaves_the_feeds_byte_identical(self):
        self.run_build([WEEK34, EMPTY])
        before = (self.root / "docs" / "menu.ics").read_bytes()
        self.run_build([WEEK34, EMPTY])
        self.assertEqual((self.root / "docs" / "menu.ics").read_bytes(), before)

    def test_archive_survives_a_week_disappearing_from_the_source(self):
        self.run_build([WEEK34, EMPTY])
        self.run_build([EMPTY, EMPTY])
        self.assertIn("to 20.8.2026", (self.root / "docs" / "menu.xml").read_text("utf-8"))

    def test_markup_change_exits_nonzero(self):
        self.assertEqual(self.run_build(["<html>redesign</html>"] * 2), 1)


if __name__ == "__main__":
    unittest.main()
