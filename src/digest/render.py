"""Render a digest to self-contained HTML, and rebuild the archive index and RSS feed."""

import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import stats
from .config import ROOT, Config
from .models import Collected, DigestSummary

SECTIONS = [
    ("tldr", "The short version"),
    ("meta", "Meta snapshot"),
    ("players", "Standout players"),
    ("news", "News"),
    ("community", "Community pulse"),
]
SOURCE_LABELS = {
    "t": "Tournament", "reddit": "Reddit", "youtube": "YouTube", "bluesky": "Bluesky",
    "inbox": "Inbox", "web": "Web", "inkdecks": "inkdecks",
}

env = Environment(
    loader=FileSystemLoader(ROOT / "templates"),
    autoescape=select_autoescape(["html", "xml", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_digest(cfg: Config, data: Collected, summary: DigestSummary | None) -> str:
    # Number citations in order of first use, like footnotes.
    lookup = {t.id: _tournament_source(t) for t in data.tournaments}
    lookup |= {i.id: _item_source(i) for i in data.items}
    numbers: dict[str, int] = {}
    sections = []
    if summary:
        for key, title in SECTIONS:
            bullets = []
            for b in getattr(summary, key):
                refs = []
                for sid in b.sources:
                    numbers.setdefault(sid, len(numbers) + 1)
                    refs.append({"n": numbers[sid], "url": lookup[sid]["url"], "title": lookup[sid]["title"]})
                bullets.append({"text": b.text, "refs": refs})
            if bullets:
                sections.append({"title": title, "bullets": bullets})

    # Each cited source, numbered like a footnote. The page's citation popovers
    # read these from an embedded JSON blob.
    sources = [{"n": n, **lookup[sid]} for sid, n in sorted(numbers.items(), key=lambda kv: kv[1])]
    return env.get_template("digest.html.j2").render(
        site=cfg["site"],
        data=data,
        summary=summary,
        sections=sections,
        sources=sources,
        pairs=stats.ink_pairs(data.tournaments)[:8],
        players=stats.repeat_players(data.tournaments)[:8],
        # inkdecks events get their own list, so keep them out of "More links".
        events=sorted(
            (i for i in data.items if i.source == "inkdecks"),
            key=lambda i: i.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True,
        ),
        uncited=[i for i in data.items if i.source != "inkdecks" and (not summary or i.id not in numbers)],
        generated=datetime.now(timezone.utc),
    )


PREVIEW_CHARS = 240


def _item_source(i) -> dict:
    meta = [i.author, i.published.strftime("%b %-d") if i.published else "", urlparse(i.url).netloc.removeprefix("www.")]
    return {
        "title": i.title,
        "url": i.url,
        "kind": SOURCE_LABELS.get(i.source, i.source),
        "meta": " · ".join(m for m in meta if m),
        "preview": _clip(i.text),
    }


def _tournament_source(t) -> dict:
    podium = "; ".join(f"{p.rank}. {p.player} ({'/'.join(sorted(p.inks))})" for p in t.podium)
    return {
        "title": t.name,
        "url": t.url,
        "kind": "Tournament",
        "meta": " · ".join(m for m in [t.date.strftime("%b %-d"), t.location, f"{t.players} players"] if m),
        "preview": podium,
    }


def _clip(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= PREVIEW_CHARS else text[:PREVIEW_CHARS].rsplit(" ", 1)[0] + "…"


def write_site(cfg: Config, site_dir: Path, slug: str, html: str, meta: dict) -> Path:
    digests = site_dir / "digests"
    digests.mkdir(parents=True, exist_ok=True)
    page = digests / f"{slug}.html"
    page.write_text(html)
    (digests / f"{slug}.json").write_text(json.dumps(meta, indent=1))
    rebuild_index(cfg, site_dir)
    return page


def rebuild_index(cfg: Config, site_dir: Path) -> None:
    entries = []
    for f in sorted((site_dir / "digests").glob("*.json"), reverse=True):
        meta = json.loads(f.read_text())
        meta["href"] = f"digests/{f.stem}.html"
        entries.append(meta)
    now = datetime.now(timezone.utc)
    (site_dir / "index.html").write_text(
        env.get_template("index.html.j2").render(site=cfg["site"], entries=entries)
    )
    (site_dir / "feed.xml").write_text(
        env.get_template("feed.xml.j2").render(
            site=cfg["site"], entries=entries[:20], updated=format_datetime(now)
        )
    )
