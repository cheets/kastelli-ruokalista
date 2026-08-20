# Kastelli lunch menu feed — design

Date: 2026-08-20
Status: approved

## Problem

Perhe.app (iPhone) renders school lunch menus from Jamix and Aromi feeds. Kastelli
school's caterer, ISS, publishes its menu only as an HTML page at
<https://ravintolapalvelut.iss.fi/kastelli/> and offers no feed of any kind. Goal:
generate an Aromi-compatible RSS feed (plus an iCalendar feed as a fallback) from that
page, refreshed automatically.

## Source analysis

The ISS page is WordPress 6.9.5 with a Ceepos menu plugin. Relevant facts, all verified
against live responses on 2026-08-20:

- The menu is **server-rendered**; no JavaScript execution is needed.
- `?date=YYYY-MM-DD` selects the week containing that date.
- Each day is a `div.day_menu_container[data-date="YYYY-MM-DD"]` holding alternating
  `div.name_price_container > h3` section headers and `span.menu_item_name` items.
- Section names observed: `Lounas`, `Kasvisruoka`, `Kasvislounas`, `Lisäkkeet`,
  `Jälkiruoka`. ISS uses `Kasvisruoka` and `Kasvislounas` interchangeably.
- `div.diets_container` is present but **always empty** for Kastelli, so no diet codes
  (L/G/M/V) can be extracted even though the page prints a legend for them.
- **Only the current week is published.** Requesting a future week returns
  `<div class="menu_not_found">Ruokalistaa ei löytynyt.</div>`.
- No prices and no serving times are published.

## Target format

The Aromi RSS feed that Perhe.app consumes natively looks like this:

```xml
<rss xmlns:atom="http://www.w3.org/2005/Atom" version="2.0"><channel>
  <title>RSS:Koulut</title><link>...</link><description />
  <item>
    <title>to 20.8.2026</title>
    <description><![CDATA[Kasvislounas:Linssi-tomaattikastike (L, M, VEGA), Simpukkapasta (L, M, VEGA)<br><br>Lounas:...]]></description>
    <guid isPermaLink="false">...</guid>
  </item>
</channel></rss>
```

Load-bearing details:

- The date lives in `item/title` as `<lowercase 2-letter Finnish weekday> d.m.yyyy`,
  with no zero padding. There is no `pubDate`.
- The description is a single CDATA string: `Section:item, item` groups joined by
  `<br><br>`, no space after the colon.
- Perhe.app splits sections on `<br><br>` and items on `, `. This means an ISS item such
  as `Nakkikastike, perunat` renders as two lines in the app, which is correct and
  desirable.
- `DateMode` on the upstream Aromi endpoint means: `0` = today, `1` = this week,
  `N` = the week `N-1` weeks from now. A static host ignores query strings, so a single
  file answers every `DateMode` value the app sends.

## Design

**Parser** (`kastelli_menu/parser.py`) — stdlib `re` + `html`. Bounds the search to the
`#week-menu` region before extracting, so stray `<h3>` elements elsewhere on the page
(e.g. the `Ravintoarvot / 100 g` nutrition popup) cannot leak into the last day. Returns
`{date: [Section(name, items)]}`. Empty weeks return `{}`, not an error.

**Store** (`kastelli_menu/store.py`) — `data/menus.json`, committed to the repo. Because
ISS exposes only one week, each run merges the freshly scraped week into an archive.
This gives the app's "previous week" arrow real content and makes a missed run harmless.
Days older than 60 days are pruned. The store carries an `updated` timestamp that is
advanced **only when the menu data actually changes**, so feed output is byte-stable
across no-op runs and the daily job produces no commit noise.

**Feeds** (`kastelli_menu/feeds.py`) — writes `docs/menu.xml` (Aromi-shaped RSS) and
`docs/menu.ics` (all-day `VEVENT` per school day, RFC 5545 line folding). No event times:
lunch is staggered per class, and the source publishes no times, so inventing a slot
would be wrong. The feed window is the last 14 days plus everything in the future.

`Kasvisruoka` is normalized to `Kasvislounas` so the app matches its known Aromi section
name and ISS's own day-to-day inconsistency disappears. Section order in output is
`Lounas`, `Kasvislounas`, `Lisäkkeet`, `Jälkiruoka` — logical rather than Aromi's
alphabetical order.

**Build** (`kastelli_menu/build.py`) — fetches the current and next week (next week is
usually empty but costs one request and picks up early publication), merges, writes.

**CI** (`.github/workflows/update-feeds.yml`) — daily at 04:00 UTC plus
`workflow_dispatch`. Commits `data/` and `docs/` when they change. GitHub Pages serves
`/docs` from `main`, so no separate deploy step is needed.

**Tests** — `tests/` runs against saved HTML fixtures (a populated week and an empty
week). No network access in the test suite.

## Deliberate non-goals

- Diet codes: the source does not provide them.
- Nutrition data and CO2 values: rendered client-side from a separate popup, out of scope.
- Honouring `DateMode` per-request: needs a dynamic host. Revisit with a Cloudflare
  Worker only if the app turns out to require it.
