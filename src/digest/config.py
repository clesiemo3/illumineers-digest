from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Account:
    name: str
    role: str = ""
    bluesky: str = ""
    youtube_channel_id: str = ""
    x: str = ""

    @property
    def priority(self) -> bool:
        return self.role in ("competitive", "pro_player", "official")


@dataclass
class Config:
    raw: dict
    accounts: list[Account]

    def __getitem__(self, key):
        return self.raw[key]


def load(root: Path = ROOT) -> Config:
    raw = yaml.safe_load((root / "config" / "sources.yaml").read_text())
    acc = yaml.safe_load((root / "config" / "accounts.yaml").read_text()) or {}
    accounts = [Account(**a) for a in (acc.get("accounts") or [])]
    return Config(raw=raw, accounts=accounts)
