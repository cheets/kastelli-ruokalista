"""Persist scraped menus.

ISS publishes only the current week, so the feed can only offer history if we
keep one. `data/menus.json` is that archive, committed alongside the feeds.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, Tuple

from .parser import Section, Week

RETENTION_DAYS = 60


def _to_json(days: Week) -> dict:
    return {
        iso: [{"name": section.name, "items": list(section.items)} for section in sections]
        for iso, sections in sorted(days.items())
    }


def _from_json(raw: dict) -> Week:
    return {
        iso: [Section(entry["name"], list(entry["items"])) for entry in sections]
        for iso, sections in raw.items()
    }


def load(path: Path) -> Tuple[Week, Optional[str]]:
    """Read the archive; a missing file is an empty archive, not an error."""
    if not path.exists():
        return {}, None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return _from_json(raw.get("days", {})), raw.get("updated")


def save(path: Path, days: Week, updated: str, source: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"updated": updated, "source": source, "days": _to_json(days)}
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def merge(existing: Week, scraped: Week, today: str) -> Tuple[Week, bool]:
    """Fold a fresh scrape into the archive and prune stale days.

    A day absent from the scrape is kept: ISS only ever serves one week, so
    absence means "not in this request", never "cancelled".
    """
    cutoff = (date.fromisoformat(today) - timedelta(days=RETENTION_DAYS)).isoformat()
    merged = {iso: sections for iso, sections in existing.items() if iso >= cutoff}
    merged.update(scraped)
    merged = dict(sorted(merged.items()))
    return merged, _to_json(merged) != _to_json(existing)
