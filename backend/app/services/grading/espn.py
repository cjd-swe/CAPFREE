"""
ESPN unofficial API — fetch only, no grading logic.
"""
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .types import GameResult, TennisMatch

ESPN_CORE_PATHS: Dict[str, str] = {
    "NBA":   "sports/basketball/leagues/nba",
    "NFL":   "sports/football/leagues/nfl",
    "NHL":   "sports/hockey/leagues/nhl",
    "MLB":   "sports/baseball/leagues/mlb",
    "NCAAB": "sports/basketball/leagues/mens-college-basketball",
}

ESPN_ENDPOINTS: Dict[str, str] = {
    "NBA":   "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    "NFL":   "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    "NHL":   "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
    "MLB":   "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    "NCAAB": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard",
}

TENNIS_ENDPOINTS: Dict[str, str] = {
    "ATP": "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard",
    "WTA": "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard",
}

# ESPN doesn't expose a dedicated Challenger tour endpoint; some events surface
# under ATP, many don't. A None-equivalent means "leave ungraded" for misses.
TENNIS_LEAGUE_FALLBACKS: Dict[str, str] = {"CHALLENGER": "ATP"}


async def fetch_scoreboard(league: str, date: datetime) -> List[GameResult]:
    """Fetch games for a league on a given date (±1 day window)."""
    if league not in ESPN_ENDPOINTS:
        return []

    url = ESPN_ENDPOINTS[league]
    games: List[GameResult] = []

    for delta in [-1, 0, 1]:
        check_date = date + timedelta(days=delta)
        date_str = check_date.strftime("%Y%m%d")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, params={"dates": date_str})
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            continue

        for event in data.get("events", []):
            try:
                comp = event["competitions"][0]
                competitors = comp["competitors"]
                if len(competitors) < 2:
                    continue
                is_final = comp.get("status", {}).get("type", {}).get("completed", False)

                scores: Dict[str, float] = {}
                names: Dict[str, str] = {}
                for c in competitors:
                    home_away = c.get("homeAway", "away")
                    names[home_away] = c["team"]["displayName"]
                    scores[home_away] = float(c.get("score", 0) or 0)

                games.append(GameResult(
                    home_team=names.get("home", ""),
                    away_team=names.get("away", ""),
                    home_score=scores.get("home", 0),
                    away_score=scores.get("away", 0),
                    is_final=is_final,
                    event_id=str(event.get("id", "")),
                ))
            except (KeyError, IndexError, ValueError):
                continue

    return games


async def fetch_tennis_matches(league: str, date: datetime) -> List[TennisMatch]:
    """
    Fetch tennis matches for a league around a given date. Doubles matches
    (competitors without an `athlete` field) are skipped.
    """
    endpoint_key = league.upper()
    endpoint_key = TENNIS_LEAGUE_FALLBACKS.get(endpoint_key, endpoint_key)
    if endpoint_key not in TENNIS_ENDPOINTS:
        return []

    url = TENNIS_ENDPOINTS[endpoint_key]
    matches: List[TennisMatch] = []
    seen_ids: set = set()

    for delta in [-1, 0, 1]:
        check_date = date + timedelta(days=delta)
        date_str = check_date.strftime("%Y%m%d")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, params={"dates": date_str})
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            continue

        for event in data.get("events", []):
            for grouping in event.get("groupings", []) or []:
                for comp in grouping.get("competitions", []) or []:
                    comp_id = comp.get("id")
                    if comp_id in seen_ids:
                        continue
                    competitors = comp.get("competitors", []) or []
                    if len(competitors) != 2:
                        continue
                    athletes = [(c.get("athlete") or {}).get("displayName") for c in competitors]
                    if not all(athletes):
                        continue
                    status = comp.get("status", {}).get("type", {})
                    matches.append(TennisMatch(
                        player1=athletes[0],
                        player2=athletes[1],
                        player1_winner=bool(competitors[0].get("winner")),
                        is_final=bool(status.get("completed")),
                        match_date=(comp.get("date") or "")[:10],
                    ))
                    if comp_id is not None:
                        seen_ids.add(comp_id)

    return matches


async def fetch_event_odds(
    event_id: str,
    core_path: str,
    pick_type: str,
    is_home_team: Optional[bool],
) -> Optional[int]:
    """Fetch closing American odds for one side of a game from ESPN core API."""
    url = (
        f"https://sports.core.api.espn.com/v2/{core_path}"
        f"/events/{event_id}/competitions/{event_id}/odds"
    )
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        items = data.get("items", [])
        if not items:
            return None
        o = items[0]
        if pick_type in ("over", "under"):
            val = o.get("overOdds" if pick_type == "over" else "underOdds")
        elif pick_type == "moneyline":
            side = "homeTeamOdds" if is_home_team else "awayTeamOdds"
            val = o.get(side, {}).get("moneyLine")
        else:  # spread
            side = "homeTeamOdds" if is_home_team else "awayTeamOdds"
            val = o.get(side, {}).get("spreadOdds")
        return int(val) if val is not None else None
    except Exception:
        return None


async def suggest_odds(
    pick_text: str,
    league: str,
    pick_date: datetime,
    games_cache: dict,
    odds_cache: dict,
) -> Optional[int]:
    """
    Re-use the already-cached scoreboard to look up closing odds for a pick.
    Must be called after grading has populated games_cache for this league/date.
    """
    from .pick_text import detect_pick_type, extract_team_from_pick_text
    from .rules import find_matching_game

    lu = league.upper()
    if lu not in ESPN_CORE_PATHS:
        return None

    key = (lu, pick_date.strftime("%Y%m%d"))
    games = games_cache.get(key)
    if not games:
        games = await fetch_scoreboard(lu, pick_date)
        if not games:
            return None
        games_cache[key] = games

    pick_type = detect_pick_type(pick_text)
    team_token = extract_team_from_pick_text(pick_text)

    full_name: Optional[str] = None
    if team_token:
        try:
            from ...ocr.teams import get_full_team_name
            full_name = get_full_team_name(team_token) or team_token
        except Exception:
            full_name = team_token

    game = find_matching_game(games, full_name or "")
    if game is None or not game.event_id:
        return None

    is_home_team: Optional[bool] = None
    if pick_type not in ("over", "under") and full_name:
        needle = full_name.lower()
        words = needle.split()
        is_home_team = (
            needle in game.home_team.lower()
            or (words and len(words[-1]) > 3 and words[-1] in game.home_team.lower())
        )

    odds_key = (game.event_id, pick_type, is_home_team)
    if odds_key in odds_cache:
        return odds_cache[odds_key]

    odds = await fetch_event_odds(game.event_id, ESPN_CORE_PATHS[lu], pick_type, is_home_team)
    odds_cache[odds_key] = odds
    return odds


class EspnSource:
    name = "espn"

    def supports(self, league: str) -> bool:
        lu = league.upper()
        endpoint_key = TENNIS_LEAGUE_FALLBACKS.get(lu, lu)
        return lu in ESPN_ENDPOINTS or endpoint_key in TENNIS_ENDPOINTS

    async def fetch(self, league: str, date: datetime, cache: dict) -> list:
        lu = league.upper()
        endpoint_key = TENNIS_LEAGUE_FALLBACKS.get(lu, lu)
        if endpoint_key in TENNIS_ENDPOINTS:
            key = (f"tennis:{endpoint_key}", date.strftime("%Y%m%d"))
            if key not in cache:
                cache[key] = await fetch_tennis_matches(lu, date)
            return cache[key]
        if lu in ESPN_ENDPOINTS:
            key = (lu, date.strftime("%Y%m%d"))
            if key not in cache:
                cache[key] = await fetch_scoreboard(lu, date)
            return cache[key]
        return []
