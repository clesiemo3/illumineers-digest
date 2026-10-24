"""Bluesky posts from tracked accounts, plus an optional "lorcana" search.

Author feeds use the public AppView and need no login. Bluesky's search
endpoint requires authentication, so the keyword search only runs when
BLUESKY_HANDLE and BLUESKY_APP_PASSWORD are set (use an app password from
Settings → Privacy and security → App passwords, never your main password).
"""

import os
from datetime import datetime

from .. import http
from ..config import Config
from ..models import Item

PUBLIC = "https://public.api.bsky.app/xrpc"
PDS = "https://bsky.social/xrpc"
SEARCH_QUERY = "lorcana"
SEARCH_MIN_LIKES = 10


def collect(cfg: Config, since: datetime) -> list[Item]:
    items: list[Item] = []
    seen: set[str] = set()
    with http.client() as c:
        for acct in cfg.accounts:
            if not acct.bluesky:
                continue
            resp = http.get(
                c, f"{PUBLIC}/app.bsky.feed.getAuthorFeed", delay=0.5,
                params={"actor": acct.bluesky, "limit": 50, "filter": "posts_no_replies"},
            )
            for entry in resp.json().get("feed", []):
                if entry.get("reason"):  # skip reposts
                    continue
                _add(items, seen, entry["post"], since, author=acct.name, priority=acct.priority)

        token = _login(c)
        if token:
            resp = http.get(
                c, f"{PDS}/app.bsky.feed.searchPosts", delay=0.5,
                headers={"Authorization": f"Bearer {token}"},
                params={"q": SEARCH_QUERY, "sort": "top", "since": since.isoformat(), "limit": 50},
            )
            for post in resp.json().get("posts", []):
                if post.get("likeCount", 0) >= SEARCH_MIN_LIKES:
                    _add(items, seen, post, since)
    return items


def _login(c) -> str | None:
    handle, password = os.environ.get("BLUESKY_HANDLE"), os.environ.get("BLUESKY_APP_PASSWORD")
    if not (handle and password):
        return None
    resp = c.post(f"{PDS}/com.atproto.server.createSession", json={"identifier": handle, "password": password})
    resp.raise_for_status()
    return resp.json()["accessJwt"]


def _add(items, seen, post, since, author="", priority=False):
    uri = post["uri"]
    created = datetime.fromisoformat(post["record"]["createdAt"].replace("Z", "+00:00"))
    if uri in seen or created < since:
        return
    seen.add(uri)
    handle = post["author"]["handle"]
    text = post["record"].get("text", "")
    items.append(
        Item(
            source="bluesky",
            title=text.split("\n", 1)[0][:120] or "(post)",
            url=f"https://bsky.app/profile/{handle}/post/{uri.rsplit('/', 1)[-1]}",
            author=author or post["author"].get("displayName") or handle,
            published=created,
            text=f"{text}\n[{post.get('likeCount', 0)} likes, {post.get('replyCount', 0)} replies]",
            priority=priority,
        )
    )
