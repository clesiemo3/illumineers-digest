import argparse
import shutil
import sys
from datetime import date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path

from . import collectors, config, render, summarize
from .models import Collected, DigestSummary

DATA = config.ROOT / "data"
SITE = config.ROOT / "site"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="digest", description="Build the Lorcana weekly digest.")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Collect, summarize and render a digest.")
    b.add_argument("--end", type=date.fromisoformat, default=date.today(), help="Last day covered (default: today).")
    b.add_argument("--days", type=int, help="Override the news window from config/sources.yaml.")
    b.add_argument("--no-ai", action="store_true", help="Skip Claude entirely and render raw results and links.")
    b.add_argument("--no-web", action="store_true", help="Skip the Claude web-search pass.")
    b.add_argument("--publish-to", type=Path, help="Copy site/ into this folder afterwards (e.g. your site repo).")
    b.add_argument(
        "--backend", choices=["claude-code", "api"],
        help="claude-code uses your Claude subscription; api uses ANTHROPIC_API_KEY. Default: config.",
    )

    c = sub.add_parser("collect", help="Only run the collectors and save what they found.")
    c.add_argument("--end", type=date.fromisoformat, default=date.today())
    c.add_argument("--days", type=int)

    r = sub.add_parser("render", help="Re-render a saved digest without fetching or calling Claude.")
    r.add_argument("slug", help="Digest date, e.g. 2026-10-26.")

    args = p.parse_args(argv)
    cfg = config.load()
    if getattr(args, "days", None):
        cfg.raw["window"]["days"] = args.days
    if getattr(args, "backend", None):
        cfg.raw["claude"]["backend"] = args.backend

    if args.cmd == "collect":
        data = _collect(cfg, args.end)
        print(f"Saved to {_save(data, None)}")
        return 0
    if args.cmd == "render":
        data, summary = _load(args.slug)
        print(f"Wrote {_write(cfg, data, summary)}")
        return 0

    data = _collect(cfg, args.end)
    summary = None
    if not args.no_ai:
        print(f"Using the {summarize.backend(cfg)} backend.")
        if not args.no_web and cfg["web_search"]["enabled"]:
            print("Searching the web for news…")
            try:
                web = summarize.web_news(cfg, data.start, data.end)
                data.items.extend(web)
                print(f"  web: {len(web)} stories")
            except Exception as e:  # noqa: BLE001
                data.errors.append(f"web search: {type(e).__name__}: {e}")
                print(f"  web search failed: {e}", file=sys.stderr)
            collectors.assign_ids(data)
        print("Summarizing with Claude…")
        summary = summarize.summarize(cfg, data)
    _save(data, summary)
    page = _write(cfg, data, summary)
    print(f"Wrote {page}")

    if args.publish_to:
        shutil.copytree(SITE, args.publish_to, dirs_exist_ok=True)
        print(f"Copied site/ to {args.publish_to}")
    return 0


def _collect(cfg, end: date) -> Collected:
    print(f"Collecting {cfg['window']['days']} days ending {end}…")
    data = collectors.collect_all(cfg, end)
    by_source: dict[str, int] = {}
    for i in data.items:
        by_source[i.source] = by_source.get(i.source, 0) + 1
    print(f"  tournaments: {len(data.tournaments)}")
    for s, n in sorted(by_source.items()):
        print(f"  {s}: {n}")
    for e in data.errors:
        print(f"  ! {e}", file=sys.stderr)
    return data


def _save(data: Collected, summary: DigestSummary | None) -> Path:
    folder = DATA / data.end.isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "collected.json").write_text(data.model_dump_json(indent=1))
    if summary:
        (folder / "summary.json").write_text(summary.model_dump_json(indent=1))
    return folder


def _load(slug: str) -> tuple[Collected, DigestSummary | None]:
    folder = DATA / slug
    data = Collected.model_validate_json((folder / "collected.json").read_text())
    s = folder / "summary.json"
    return data, DigestSummary.model_validate_json(s.read_text()) if s.exists() else None


def _write(cfg, data: Collected, summary: DigestSummary | None) -> Path:
    html = render.render_digest(cfg, data, summary)
    meta = {
        "title": summary.headline if summary else f"This week in Lorcana ({data.end:%b %-d})",
        "start": data.start.isoformat(),
        "end": data.end.isoformat(),
        "published": format_datetime(datetime.now(timezone.utc)),
        "summary": [b.text for b in summary.tldr] if summary else [],
    }
    return render.write_site(cfg, SITE, data.end.isoformat(), html, meta)


if __name__ == "__main__":
    sys.exit(main())
