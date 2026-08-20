"""Scrape ISS, merge into the archive, and write the feeds under `docs/`."""

from __future__ import annotations

import argparse
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, List

from . import store
from .feeds import SITE_URL, render_ics, render_rss
from .parser import Week, parse_week, week_is_published

USER_AGENT = "kastelli-ruokalista/1.0 (+https://github.com/)"
TIMEOUT = 30

# How much of the archive the published feeds carry. Two weeks of history keeps
# Perhe.app's "previous week" arrow populated without bloating the files.
HISTORY_DAYS = 14

Fetcher = Callable[[str], str]


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", "replace")


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def scrape(today: date, fetcher: Fetcher = fetch) -> tuple[Week, List[str]]:
    """Scrape this week and the next one, returning the menu and any warnings.

    Next week is nearly always empty — ISS publishes one week at a time — but the
    extra request is cheap and picks the new week up the moment it appears.
    """
    scraped: Week = {}
    warnings: List[str] = []
    for offset in (0, 1):
        monday = monday_of(today) + timedelta(weeks=offset)
        url = f"{SITE_URL}?date={monday.isoformat()}"
        page = fetcher(url)
        week = parse_week(page)
        if not week and week_is_published(page):
            warnings.append(
                f"{url}: no days parsed and no 'menu not found' notice — "
                "the page markup may have changed"
            )
        scraped.update(week)
    return scraped, warnings


def feed_window(days: Week, today: date) -> Week:
    cutoff = (today - timedelta(days=HISTORY_DAYS)).isoformat()
    return {iso: sections for iso, sections in days.items() if iso >= cutoff}


def build(
    data_path: Path,
    out_dir: Path,
    today: date,
    fetcher: Fetcher = fetch,
) -> int:
    scraped, warnings = scrape(today, fetcher)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    existing, previous_updated = store.load(data_path)
    merged, changed = store.merge(existing, scraped, today=today.isoformat())

    updated = (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if changed or previous_updated is None
        else previous_updated
    )
    store.save(data_path, merged, updated=updated, source=SITE_URL)

    published = feed_window(merged, today)
    out_dir.mkdir(parents=True, exist_ok=True)
    # newline="" keeps the ICS CRLF pairs intact on every platform; without it a
    # Windows runner would rewrite "\r\n" as "\r\r\n".
    (out_dir / "menu.xml").write_text(
        render_rss(published, updated), encoding="utf-8", newline="\n"
    )
    (out_dir / "menu.ics").write_text(
        render_ics(published, updated), encoding="utf-8", newline=""
    )

    print(
        f"{len(scraped)} day(s) scraped, {len(merged)} archived, "
        f"{len(published)} in feeds, changed={changed}"
    )
    # Warn but do not fail on an empty scrape: school holidays are legitimately empty.
    return 1 if warnings else 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/menus.json"))
    parser.add_argument("--out", type=Path, default=Path("docs"))
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=None,
        help="Override today's date (ISO), for reproducible runs and testing.",
    )
    args = parser.parse_args(argv)
    today = args.today or datetime.now(timezone.utc).date()
    return build(args.data, args.out, today)


if __name__ == "__main__":
    raise SystemExit(main())
