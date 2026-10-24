"""Top posts of the week from Reddit's public RSS feed (no API key needed)."""

from datetime import datetime

import feedparser
from bs4 import BeautifulSoup

from .. import http
from ..config import Config
from ..models import Item


def collect(cfg: Config, since: datetime) -> list[Item]:
    opts = cfg["reddit"]
    items = []
    with http.client() as c:
        for sub in opts["subreddits"]:
            url = f"https://www.reddit.com/r/{sub}/top/.rss"
            feed = feedparser.parse(http.get(c, url, params={"t": "week", "limit": opts["limit"]}).text)
            for e in feed.entries:
                published = _date(e)
                if published and published < since:
                    continue
                body = BeautifulSoup(e.get("summary", ""), "html.parser").select_one(".md")
                items.append(
                    Item(
                        source="reddit",
                        title=e.title,
                        url=e.link,
                        author=e.get("author", "").removeprefix("/u/"),
                        published=published,
                        text=body.get_text(" ", strip=True)[:1500] if body else "",
                    )
                )
    return items


def _date(entry) -> datetime | None:
    raw = entry.get("published") or entry.get("updated")
    return datetime.fromisoformat(raw) if raw else None
