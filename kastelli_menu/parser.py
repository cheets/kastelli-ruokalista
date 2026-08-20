"""Parse the Ceepos week menu embedded in the ISS restaurant page.

The page is server-rendered WordPress, so plain regex extraction is enough and
avoids a third-party HTML parser dependency in CI.
"""

from __future__ import annotations

import html
import re
from typing import Dict, List, NamedTuple


class Section(NamedTuple):
    """One meal section of a day, e.g. Lounas with its dishes."""

    name: str
    items: List[str]


Week = Dict[str, List[Section]]

# ISS uses both spellings for the vegetarian section, sometimes within one week.
# Aromi — and therefore Perhe.app's section styling — knows only "Kasvislounas".
SECTION_ALIASES = {"Kasvisruoka": "Kasvislounas"}

# Emitted by the plugin when the requested week has no menu published yet.
_NOT_FOUND = 'class="menu_not_found"'

_REGION_START = '<div class="restaurant_menu_container" id="week-menu">'
_REGION_END = '<div class="die_happy_container">'

_DAY = re.compile(r'<div class="day_menu_container" data-date="(\d{4}-\d{2}-\d{2})"')
_ENTRY = re.compile(
    r'<div class="name_price_container">\s*<h3>(?P<section>.*?)</h3>'
    r'|<span class="menu_item_name">(?P<item>.*?)</span>',
    re.S,
)
_TAGS = re.compile(r"<[^>]+>")


def _clean(raw: str) -> str:
    return html.unescape(_TAGS.sub("", raw)).replace("\xa0", " ").strip()


def _menu_region(page: str) -> str:
    """Narrow the page to the week menu.

    Without this bound, `<h3>` elements from the nutrition popup that follows the
    menu (`Ravintoarvot / 100 g`) would be picked up as a section of the last day.
    """
    start = page.find(_REGION_START)
    if start == -1:
        return ""
    end = page.find(_REGION_END, start)
    return page[start:] if end == -1 else page[start:end]


def week_is_published(page: str) -> bool:
    """False when the page explicitly says no menu exists for the requested week."""
    return _NOT_FOUND not in _menu_region(page)


def parse_day(chunk: str) -> List[Section]:
    """Extract the sections of a single `day_menu_container` fragment."""
    sections: List[Section] = []
    for match in _ENTRY.finditer(chunk):
        if match.group("section") is not None:
            name = _clean(match.group("section"))
            if not name:
                continue
            sections.append(Section(SECTION_ALIASES.get(name, name), []))
        else:
            item = _clean(match.group("item"))
            if item and sections:
                sections[-1].items.append(item)
    return [section for section in sections if section.items]


def parse_week(page: str) -> Week:
    """Extract every day of the week menu, keyed by ISO date."""
    region = _menu_region(page)
    starts = [(m.group(1), m.start()) for m in _DAY.finditer(region)]
    week: Week = {}
    for index, (date, offset) in enumerate(starts):
        end = starts[index + 1][1] if index + 1 < len(starts) else len(region)
        sections = parse_day(region[offset:end])
        if sections:
            week[date] = sections
    return week
