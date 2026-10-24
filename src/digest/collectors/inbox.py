"""Hand-curated links from inbox.md (Facebook group posts and anything else)."""

import re
from datetime import date, datetime, timezone

from ..config import ROOT
from ..models import Item

HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")
ENTRY = re.compile(r"^[-*]\s+(https?://\S+)\s*(?:[—–-]+\s*)?(.*)$")


def collect(start: date, end: date, path=None) -> list[Item]:
    path = path or ROOT / "inbox.md"
    if not path.exists():
        return []
    items, current, in_fence = [], None, False
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("```"):  # examples live in fenced blocks
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if m := HEADING.match(line):
            current = date.fromisoformat(m.group(1))
            continue
        m = ENTRY.match(line)
        if not (m and current and start <= current <= end):
            continue
        url, note = m.group(1), m.group(2).strip()
        items.append(
            Item(
                source="inbox",
                title=note or url,
                url=url,
                author="Facebook group" if "facebook.com" in url else "",
                published=datetime.combine(current, datetime.min.time(), tzinfo=timezone.utc),
                text=note,
            )
        )
    return items
