"""Render a digest to self-contained HTML, and rebuild the archive index and RSS feed."""

import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

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
    "inbox": "Inbox", "web": "Web",
}

env = Environment(
    loader=FileSystemLoader(ROOT / "templates"),
    autoescape=select_autoescape(["html", "xml", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_digest(cfg: Config, data: Collected, summary: DigestSummary | None) -> str:
    # Number citations in order of first use, like footnotes.
    lookup = {t.id: (t.name, t.url, "Tournament") for t in data.tournaments}
    lookup |= {i.id: (i.title, i.url, SOURCE_LABELS.get(i.source, i.source)) for i in data.items}
    numbers: dict[str, int] = {}
    sections = []
    if summary:
        for key, title in SECTIONS:
            bullets = []
            for b in getattr(summary, key):
                refs = []
                for sid in b.sources:
                    numbers.setdefault(sid, len(numbers) + 1)
                    refs.append({"n": numbers[sid], "url": lookup[sid][1], "title": lookup[sid][0]})
                bullets.append({"text": b.text, "refs": refs})
            if bullets:
                sections.append({"title": title, "bullets": bullets})

    sources = [
        {"n": n, "title": lookup[sid][0], "url": lookup[sid][1], "kind": lookup[sid][2]}
        for sid, n in sorted(numbers.items(), key=lambda kv: kv[1])
    ]
    return env.get_template("digest.html.j2").render(
        site=cfg["site"],
        data=data,
        summary=summary,
        sections=sections,
        sources=sources,
        pairs=stats.ink_pairs(data.tournaments)[:8],
        players=stats.repeat_players(data.tournaments)[:8],
        uncited=[i for i in data.items if i.id not in numbers] if summary else data.items,
        generated=datetime.now(timezone.utc),
    )


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
