"""Tournament results from lorcanahunter.com.

Lorcanahunter's robots.txt allows crawlers on these pages. inkdecks.com does
not (it blocks AI crawlers and sits behind a Cloudflare challenge), so it is
deliberately not used.
"""

import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from .. import http
from ..config import Config
from ..models import MetaShare, Placement, Tournament

BASE = "https://lorcanahunter.com"
LIST_URL = BASE + "/en/past-events"


def collect(cfg: Config, start: date, end: date) -> list[Tournament]:
    opts = cfg["tournaments"]
    found: list[Tournament] = []
    with http.client() as c:
        for page in range(1, opts["max_pages"] + 1):
            html = http.get(c, LIST_URL, params={"page": page} if page > 1 else None).text
            events = parse_list(html)
            if not events:
                break
            found += [t for t in events if start <= t.date <= end and t.players >= opts["min_players"]]
            # Newest first, so stop once a page ends before the window.
            if events[-1].date < start:
                break
    found.sort(key=lambda t: (t.date, t.players), reverse=True)
    return found


def parse_list(html: str) -> list[Tournament]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for art in soup.select("article.lh-tt"):
        banner = art.select_one("a.lh-tt-banner")
        title = art.select_one(".lh-tt-title")
        if not banner or not title:
            continue
        meta_text = " ".join(s.get_text(" ", strip=True) for s in art.select(".lh-tt-meta > span"))
        when = re.search(r"\d{1,2} \w{3} \d{4}", meta_text)
        if not when:
            continue
        kicker = art.select_one(".lh-tt-kicker")
        badge = art.select_one(".lh-tt-badge")
        out.append(
            Tournament(
                name=title.get_text(strip=True),
                url=BASE + banner["href"],
                date=datetime.strptime(when.group(0), "%d %b %Y").date(),
                location=kicker.get_text(" ", strip=True).replace(" | ", " · ") if kicker else "",
                tier=badge.get_text(strip=True) if badge else "",
                players=_int(r"(\d[\d,]*) players", meta_text),
                decklists=_int(r"(\d[\d,]*) decklists", meta_text),
                podium=[_placement(a) for a in art.select("a.lh-tt-podium-row")],
                meta=[_share(a) for a in art.select('a[href*="/bico/"]')],
            )
        )
    return out


def _placement(a) -> Placement:
    rank = a.select_one(".lh-tt-rank")
    player = a.select_one(".lh-tt-player")
    return Placement(
        rank=int(rank.get_text(strip=True)) if rank else 0,
        player=player.get_text(strip=True) if player else "?",
        inks=_inks(a),
        deck_url=BASE + a["href"],
    )


def _share(a) -> MetaShare:
    text = a.get_text(" ", strip=True)
    pct = re.search(r"([\d.]+)%", text)
    return MetaShare(
        inks=_inks(a),
        pct=float(pct.group(1)) if pct else 0.0,
        decks=_int(r"(\d+) decks?", text),
    )


def _inks(el) -> list[str]:
    return [img["alt"] for img in el.select("img[src*='dlc_ink_']") if img.get("alt")]


def _int(pattern: str, text: str) -> int:
    m = re.search(pattern, text)
    return int(m.group(1).replace(",", "")) if m else 0
