"""Events from inkdecks' tournament RSS feed (used with the site owner's permission).

Only the feed's title, description and link are used; decklists are never
fetched. Cloudflare currently blocks scripts from the feed, so the collector
tries the live URL first and falls back to a copy saved from your browser
(inkdecks.rss in the project folder, not committed to git).
"""

import calendar
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import httpx
from bs4 import BeautifulSoup

from .. import http
from ..config import ROOT, Config
from ..models import Item

FEED_URL = "https://inkdecks.com/lorcana-tournaments/feed.rss"
STALE_AFTER = timedelta(days=3)


def collect(cfg: Config, since: datetime) -> list[Item]:
    opts = cfg["tournaments"].get("inkdecks") or {}
    if not opts.get("enabled", True):
        return []
    xml = _fetch_live(opts.get("url", FEED_URL))
    if xml is None:
        xml = _read_saved(ROOT / Path(opts.get("saved_file", "inkdecks.rss")).expanduser())

    feed = feedparser.parse(xml)
    if feed.bozo and not feed.entries:
        raise ValueError(f"couldn't parse the inkdecks feed: {feed.bozo_exception}")

    items = []
    for e in feed.entries:
        description = BeautifulSoup(e.get("description", ""), "html.parser").get_text(" ", strip=True)
        m = DESCRIPTION.search(description)
        # The feed has no pubDate; the event date is in the description.
        published = _event_date(m) if m else _date(e)
        if not published or published < since:
            continue
        items.append(
            Item(
                source="inkdecks",
                title=e.get("title", "").strip() or e.link,
                url=e.link,
                author="inkdecks",
                published=published,
                text=_summary(m) if m else description[:800],
            )
        )
    return items


# "... @ Store (US) took place on October 24, 2026 featuring 79 players.
#  Winner of the event: Darian with Cortisol Down, Paws Up."
DESCRIPTION = re.compile(
    r"\((?P<country>[A-Z]{2})\) took place on (?P<date>\w+ \d{1,2}, \d{4})"
    r"(?: featuring (?P<players>\d+) players)?\."
    r"(?: Winner of the event: (?P<winner>.+?) with (?P<deck>.+?)\.)?\s*$"
)


def _event_date(m) -> datetime:
    return datetime.strptime(m["date"], "%B %d, %Y").replace(tzinfo=timezone.utc)


def _summary(m) -> str:
    parts = [f"Event on {m['date']} in {m['country']}"]
    if m["players"]:
        parts[0] += f", {m['players']} players"
    if m["winner"]:
        # The deck name is whatever the winner titled their list, not its ink colors.
        parts.append(f"Winner: {m['winner']} with a deck titled “{m['deck']}”")
    return ". ".join(parts) + "."


def _fetch_live(url: str) -> str | None:
    try:
        with http.client() as c:
            resp = http.get(c, url, delay=0)
        return resp.text if "<rss" in resp.text[:2000] or "<feed" in resp.text[:2000] else None
    except httpx.HTTPError:
        return None


def _read_saved(path) -> str:
    if not path.exists():
        raise FileNotFoundError(
            f"live feed blocked and no saved copy. Open {FEED_URL} in your browser "
            f"and save it as {path.name} in the project folder."
        )
    age = datetime.now(timezone.utc) - datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    if age > STALE_AFTER:
        print(f"  ! inkdecks: saved feed is {age.days} days old; save a fresh copy for new events.", file=sys.stderr)
    return path.read_text()


def _date(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime.fromtimestamp(calendar.timegm(parsed), timezone.utc) if parsed else None
