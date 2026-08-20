import unittest

from kastelli_menu.feeds import fold_ics_line, render_ics, render_rss
from kastelli_menu.parser import Section

MENU = {
    "2026-08-20": [
        Section("Lounas", ["Lohipastavuoka"]),
        Section("Kasvislounas", ["Juustoinen pastavuoka"]),
        Section("Lisäkkeet", ["Jäävuori-kurkku-hernesalaatti, punajuuri"]),
    ],
    "2026-08-21": [
        Section("Lounas", ["Pinaattiohukaiset, perunasose"]),
        Section("Lisäkkeet", ["Porkkana-raejuustoraaste, puolukkahillo"]),
    ],
}
STAMP = "2026-08-20T04:00:00Z"


class RenderRssTest(unittest.TestCase):
    def setUp(self):
        self.xml = render_rss(MENU, updated=STAMP)

    def test_is_rss_2_with_atom_namespace(self):
        self.assertIn('<rss xmlns:atom="http://www.w3.org/2005/Atom" version="2.0">', self.xml)

    def test_item_title_is_finnish_short_date(self):
        # lowercase two-letter weekday, no zero padding, as Aromi emits.
        self.assertIn("<title>to 20.8.2026</title>", self.xml)
        self.assertIn("<title>pe 21.8.2026</title>", self.xml)

    def test_description_joins_sections_with_double_br_and_no_space_after_colon(self):
        self.assertIn(
            "<![CDATA[Lounas:Lohipastavuoka<br><br>Kasvislounas:Juustoinen pastavuoka"
            "<br><br>Lisäkkeet:Jäävuori-kurkku-hernesalaatti, punajuuri]]>",
            self.xml,
        )

    def test_items_within_a_section_are_comma_joined(self):
        xml = render_rss(
            {"2026-08-20": [Section("Lounas", ["Keitto", "Leipä"])]}, updated=STAMP
        )
        self.assertIn("Lounas:Keitto, Leipä", xml)

    def test_days_are_ordered_chronologically(self):
        self.assertLess(self.xml.index("to 20.8.2026"), self.xml.index("pe 21.8.2026"))

    def test_guid_is_not_a_permalink_and_is_unique_per_day(self):
        self.assertEqual(self.xml.count('<guid isPermaLink="false">'), 2)

    def test_escapes_xml_metacharacters_in_titles(self):
        xml = render_rss({"2026-08-20": [Section("Lounas", ["Kala & peruna"])]}, updated=STAMP)
        self.assertIn("Kala & peruna", xml)  # inside CDATA, left raw
        self.assertNotIn("<channel>&", xml)

    def test_is_wellformed_xml(self):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(self.xml)
        self.assertEqual(len(root.findall("./channel/item")), 2)


class RenderIcsTest(unittest.TestCase):
    def setUp(self):
        self.ics = render_ics(MENU, updated=STAMP)
        self.unfolded = self.ics.replace("\r\n ", "")

    def test_has_calendar_envelope(self):
        self.assertTrue(self.ics.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(self.ics.endswith("END:VCALENDAR\r\n"))

    def test_uses_crlf_line_endings(self):
        self.assertNotIn("\n", self.ics.replace("\r\n", ""))

    def test_events_are_all_day(self):
        self.assertIn("DTSTART;VALUE=DATE:20260820\r\n", self.ics)
        self.assertIn("DTEND;VALUE=DATE:20260821\r\n", self.ics)
        self.assertNotIn("DTSTART:", self.ics)

    def test_summary_is_the_main_course(self):
        self.assertIn("SUMMARY:Lohipastavuoka\r\n", self.unfolded)

    def test_description_escapes_newlines_and_commas(self):
        unfolded = self.ics.replace("\r\n ", "")
        self.assertIn("Lisäkkeet: Jäävuori-kurkku-hernesalaatti\\, punajuuri", unfolded)
        self.assertIn("Lounas: Lohipastavuoka\\nKasvislounas:", unfolded)

    def test_dtstamp_comes_from_the_store_not_the_clock(self):
        self.assertIn("DTSTAMP:20260820T040000Z", self.ics)

    def test_uid_is_stable_per_day(self):
        self.assertIn("UID:2026-08-20@kastelli-ruokalista", self.ics)

    def test_folds_long_lines_to_75_octets(self):
        for line in self.ics.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75, line)


class FoldTest(unittest.TestCase):
    def test_short_line_is_untouched(self):
        self.assertEqual(fold_ics_line("SUMMARY:Kala"), "SUMMARY:Kala")

    def test_continuation_lines_start_with_a_space(self):
        folded = fold_ics_line("SUMMARY:" + "a" * 200).split("\r\n")
        self.assertTrue(all(part.startswith(" ") for part in folded[1:]))

    def test_never_splits_a_multibyte_character(self):
        folded = fold_ics_line("SUMMARY:" + "ä" * 120)
        self.assertEqual(folded.replace("\r\n ", ""), "SUMMARY:" + "ä" * 120)


if __name__ == "__main__":
    unittest.main()
