"""Deterministic tournament numbers, so the digest never relies on Claude for arithmetic."""

from collections import defaultdict
from dataclasses import dataclass, field

from .models import Tournament


@dataclass
class PairStats:
    inks: tuple[str, ...]
    wins: int = 0
    podiums: int = 0
    events: set[str] = field(default_factory=set)

    @property
    def label(self) -> str:
        return "/".join(self.inks)


@dataclass
class PlayerStats:
    name: str
    wins: int = 0
    podiums: int = 0
    events: list[str] = field(default_factory=list)


def ink_pairs(tournaments: list[Tournament]) -> list[PairStats]:
    pairs: dict[tuple[str, ...], PairStats] = {}
    for t in tournaments:
        for p in t.podium:
            key = tuple(sorted(p.inks))
            s = pairs.setdefault(key, PairStats(inks=key))
            s.podiums += 1
            s.wins += p.rank == 1
            s.events.add(t.id)
    return sorted(pairs.values(), key=lambda s: (s.wins, s.podiums), reverse=True)


def repeat_players(tournaments: list[Tournament]) -> list[PlayerStats]:
    players: dict[str, PlayerStats] = defaultdict(lambda: PlayerStats(name=""))
    for t in tournaments:
        for p in t.podium:
            s = players[p.player.casefold()]
            s.name = s.name or p.player
            s.podiums += 1
            s.wins += p.rank == 1
            s.events.append(t.id)
    return sorted((s for s in players.values() if s.podiums > 1), key=lambda s: (s.wins, s.podiums), reverse=True)
