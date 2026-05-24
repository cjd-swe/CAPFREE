"""
Sofascore fallback for tennis grading — fetch only, no grading logic.

ESPN's tennis scoreboard only covers ATP/WTA main-tour events. Challengers,
ITF, and minor doubles draws are absent. Sofascore has full coverage but sits
behind Cloudflare; curl_cffi impersonates Chrome's TLS handshake to get through.

Unofficial API, undocumented, may break without notice.
"""
from datetime import datetime, timedelta
from typing import List

from curl_cffi.requests import AsyncSession

from .types import TennisMatch
from .pick_text import _ascii_fold

_SCHEDULED_URL = "https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/{date}"
_IMPERSONATE = "chrome120"

_TENNIS_LEAGUES = frozenset({"ATP", "WTA", "CHALLENGER", "ITF"})


def _event_to_tennis_match(event: dict):
    home = event.get("homeTeam") or {}
    away = event.get("awayTeam") or {}
    home_name = _ascii_fold(home.get("name") or "")
    away_name = _ascii_fold(away.get("name") or "")
    if not home_name or not away_name:
        return None

    winner_code = event.get("winnerCode")
    status_type = (event.get("status") or {}).get("type", "")
    is_final = status_type == "finished"

    start = event.get("startTimestamp")
    match_date = ""
    if start:
        try:
            match_date = datetime.utcfromtimestamp(int(start)).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError):
            match_date = ""

    return TennisMatch(
        player1=home_name,
        player2=away_name,
        player1_winner=(winner_code == 1),
        is_final=is_final,
        match_date=match_date,
    )


async def fetch_tennis_matches_sofascore(
    date: datetime, window_days: int = 2
) -> List[TennisMatch]:
    """
    Fetch tennis matches (singles + doubles) from Sofascore across a ±window_days
    range. Returns empty list on any transport error.
    """
    out: List[TennisMatch] = []
    seen_ids: set = set()

    async with AsyncSession() as session:
        for delta in range(-window_days, window_days + 1):
            day = date + timedelta(days=delta)
            url = _SCHEDULED_URL.format(date=day.strftime("%Y-%m-%d"))
            try:
                resp = await session.get(url, impersonate=_IMPERSONATE, timeout=10)
                if resp.status_code != 200:
                    continue
                data = resp.json()
            except Exception:
                continue

            for ev in data.get("events", []) or []:
                ev_id = ev.get("id")
                if ev_id in seen_ids:
                    continue
                tm = _event_to_tennis_match(ev)
                if tm is None:
                    continue
                out.append(tm)
                if ev_id is not None:
                    seen_ids.add(ev_id)

    return out


class SofascoreSource:
    name = "sofascore"

    def supports(self, league: str) -> bool:
        return league.upper() in _TENNIS_LEAGUES

    async def fetch(self, league: str, date: datetime, cache: dict) -> list:
        key = ("sofa:tennis", date.strftime("%Y%m%d"))
        if key not in cache:
            cache[key] = await fetch_tennis_matches_sofascore(date)
        return cache[key]
