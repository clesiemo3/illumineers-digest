from datetime import date, datetime, timedelta, timezone

from ..config import Config
from ..models import Collected
from . import bluesky, inbox, inkdecks, lorcanahunter, reddit, youtube


def collect_all(cfg: Config, end: date) -> Collected:
    days = cfg["window"]["days"]
    start = end - timedelta(days=days)
    since = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    out = Collected(start=start, end=end)

    t_start = end - timedelta(days=cfg["window"]["tournament_days"])
    _run(out, "lorcanahunter", lambda: out.tournaments.extend(lorcanahunter.collect(cfg, t_start, end)))
    _run(out, "inkdecks", lambda: out.items.extend(inkdecks.collect(cfg, since)))
    _run(out, "reddit", lambda: out.items.extend(reddit.collect(cfg, since)))
    _run(out, "youtube", lambda: out.items.extend(youtube.collect(cfg, since)))
    _run(out, "bluesky", lambda: out.items.extend(bluesky.collect(cfg, since)))
    _run(out, "inbox", lambda: out.items.extend(inbox.collect(start, end)))
    assign_ids(out)
    return out


def assign_ids(out: Collected) -> None:
    for i, t in enumerate(out.tournaments, 1):
        t.id = f"t-{i}"
    counts: dict[str, int] = {}
    for item in out.items:
        counts[item.source] = counts.get(item.source, 0) + 1
        item.id = f"{item.source}-{counts[item.source]}"


def _run(out: Collected, name: str, fn) -> None:
    # One broken source shouldn't sink the whole digest.
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        out.errors.append(f"{name}: {type(e).__name__}: {e}")
