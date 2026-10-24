"""New uploads from tracked YouTube channels via their public RSS feeds."""

from datetime import datetime

import feedparser

from .. import http
from ..config import Config
from ..models import Item

FEED = "https://www.youtube.com/feeds/videos.xml"


def collect(cfg: Config, since: datetime) -> list[Item]:
    items = []
    with http.client() as c:
        for acct in cfg.accounts:
            if not acct.youtube_channel_id:
                continue
            feed = feedparser.parse(http.get(c, FEED, params={"channel_id": acct.youtube_channel_id}).text)
            for e in feed.entries:
                published = datetime.fromisoformat(e.published)
                if published < since:
                    continue
                items.append(
                    Item(
                        source="youtube",
                        title=e.title,
                        url=e.link,
                        author=acct.name,
                        published=published,
                        text=(e.get("summary") or "")[:1000],
                        priority=acct.priority,
                    )
                )
    return items
