from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Protocol


@dataclass
class GameResult:
    home_team: str
    away_team: str
    home_score: float
    away_score: float
    is_final: bool
    event_id: Optional[str] = field(default=None)


@dataclass
class TennisMatch:
    player1: str
    player2: str
    player1_winner: bool  # meaningful only when is_final
    is_final: bool
    match_date: str  # ISO date, e.g. "2026-04-14"


class DataSource(Protocol):
    name: str

    def supports(self, league: str) -> bool:
        ...

    async def fetch(self, league: str, date: datetime, cache: dict) -> list:
        ...
