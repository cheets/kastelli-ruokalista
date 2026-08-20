"""Render the parsed menu as Aromi-compatible RSS and as iCalendar."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, List
from xml.sax.saxutils import escape

from .parser import Section, Week

SITE_URL = "https://ravintolapalvelut.iss.fi/kastelli/"
CHANNEL_TITLE = "RSS:Kastelli"
CALENDAR_NAME = "Kastellin koulu – kouluruoka"
UID_DOMAIN = "kastelli-ruokalista"

# Perhe.app renders sections in feed order, so put the main course first rather
# than following Aromi's alphabetical ordering. Unknown sections sort last.
SECTION_ORDER = ("Lounas", "Kasvislounas", "Lisäkkeet", "Jälkiruoka")

WEEKDAYS_FI = ("ma", "ti", "ke", "to", "pe", "la", "su")


def finnish_date(day: date) -> str:
    """`to 20.8.2026` — the exact shape Aromi puts in `item/title`."""
    return f"{WEEKDAYS_FI[day.weekday()]} {day.day}.{day.month}.{day.year}"


def ordered_sections(sections: Iterable[Section]) -> List[Section]:
    def key(item):
        index, section = item
        try:
            return (SECTION_ORDER.index(section.name), index)
        except ValueError:
            return (len(SECTION_ORDER), index)

    return [section for _, section in sorted(enumerate(sections), key=key)]


def main_course(sections: Iterable[Section]) -> str:
    sections = list(sections)
    for section in sections:
        if section.name == "Lounas" and section.items:
            return section.items[0]
    return sections[0].items[0] if sections and sections[0].items else "Kouluruoka"


# --------------------------------------------------------------------------- RSS


def _cdata(text: str) -> str:
    # A literal "]]>" would close the section early; split it across two sections.
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def _rss_description(sections: Iterable[Section]) -> str:
    # "Section:item, item" groups joined by <br><br>, no space after the colon.
    # Perhe.app splits on exactly these separators.
    return "<br><br>".join(
        f"{section.name}:{', '.join(section.items)}" for section in sections
    )


def render_rss(days: Week, updated: str) -> str:
    """Build an RSS 2.0 document shaped like the Aromi school-menu feed."""
    del updated  # Aromi publishes no pubDate; kept for a uniform renderer signature.
    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<rss xmlns:atom="http://www.w3.org/2005/Atom" version="2.0">',
        "<channel>",
        f"<title>{escape(CHANNEL_TITLE)}</title>",
        f"<link>{escape(SITE_URL)}</link>",
        "<description />",
    ]
    for iso in sorted(days):
        sections = ordered_sections(days[iso])
        title = finnish_date(date.fromisoformat(iso))
        parts += [
            "<item>",
            f"<title>{escape(title)}</title>",
            f"<description>{_cdata(_rss_description(sections))}</description>",
            f'<guid isPermaLink="false">{escape(SITE_URL)}?date={iso}</guid>',
            "</item>",
        ]
    parts += ["</channel>", "</rss>", ""]
    return "\n".join(parts)


# --------------------------------------------------------------------------- ICS


def fold_ics_line(line: str, limit: int = 75) -> str:
    """Fold to RFC 5545's 75-octet limit without splitting a UTF-8 character."""
    if len(line.encode("utf-8")) <= limit:
        return line
    chunks: List[str] = []
    current = b""
    first = True
    for char in line:
        encoded = char.encode("utf-8")
        cap = limit if first else limit - 1  # continuations spend one octet on the space
        if len(current) + len(encoded) > cap:
            chunks.append(current.decode("utf-8"))
            current = b""
            first = False
        current += encoded
    chunks.append(current.decode("utf-8"))
    return chunks[0] + "".join("\r\n " + chunk for chunk in chunks[1:])


def escape_ics_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _ics_stamp(updated: str) -> str:
    moment = datetime.fromisoformat(updated.replace("Z", "+00:00"))
    return moment.strftime("%Y%m%dT%H%M%SZ")


def render_ics(days: Week, updated: str) -> str:
    """Build an iCalendar feed of all-day events, one per school day.

    No event times: lunch is staggered by class and the source publishes no
    serving hours, so any clock time would be invented.
    """
    stamp = _ics_stamp(updated)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{UID_DOMAIN}//FI",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics_text(CALENDAR_NAME)}",
        "X-WR-TIMEZONE:Europe/Helsinki",
    ]
    for iso in sorted(days):
        sections = ordered_sections(days[iso])
        start = date.fromisoformat(iso)
        body = "\n".join(
            f"{section.name}: {', '.join(section.items)}" for section in sections
        )
        lines += [
            "BEGIN:VEVENT",
            f"UID:{iso}@{UID_DOMAIN}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(start + timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{escape_ics_text(main_course(sections))}",
            f"DESCRIPTION:{escape_ics_text(body)}",
            f"URL:{SITE_URL}?date={iso}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "".join(fold_ics_line(line) + "\r\n" for line in lines)
