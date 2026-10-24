from datetime import date, datetime

from pydantic import BaseModel, Field


class Item(BaseModel):
    """One piece of collected content. `id` is what Claude cites."""

    id: str = ""
    source: str  # reddit | youtube | bluesky | inbox | web
    title: str
    url: str
    author: str = ""
    published: datetime | None = None
    text: str = ""
    priority: bool = False


class Placement(BaseModel):
    rank: int
    player: str
    inks: list[str]
    deck_url: str


class MetaShare(BaseModel):
    inks: list[str]
    pct: float
    decks: int


class Tournament(BaseModel):
    id: str = ""
    name: str
    url: str
    date: date
    location: str = ""
    tier: str = ""
    players: int = 0
    decklists: int = 0
    podium: list[Placement] = Field(default_factory=list)
    meta: list[MetaShare] = Field(default_factory=list)


class Collected(BaseModel):
    start: date
    end: date
    tournaments: list[Tournament] = Field(default_factory=list)
    items: list[Item] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# --- Claude's structured output ---------------------------------------------


class Bullet(BaseModel):
    text: str = Field(description="One or two sentences. Plain text, no markdown.")
    sources: list[str] = Field(
        description="IDs of the collected items or tournaments this bullet is based on, e.g. ['reddit-3', 't-2']."
    )


class DigestSummary(BaseModel):
    headline: str = Field(description="A short, specific headline for the week.")
    tldr: list[Bullet] = Field(description="3-5 bullets: the most important things that happened.")
    meta: list[Bullet] = Field(description="What decks and ink pairs are winning, and what changed.")
    players: list[Bullet] = Field(description="Standout players and results.")
    news: list[Bullet] = Field(description="Official announcements, set news, bans, organized play.")
    community: list[Bullet] = Field(description="Notable community discussion, videos and posts.")
