"""
ESPN unofficial API service for auto-grading picks.
No API key required.
"""
import httpx
import asyncio
import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

ESPN_ENDPOINTS = {
    "NBA":   "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    "NFL":   "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    "NHL":   "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
    "MLB":   "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    "NCAAB": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard",
}

# Tennis scoreboards have a different response shape (events → groupings →
# competitions) and the "teams" are individual athletes. Handled via a
# separate fetch/grade path below.
TENNIS_ENDPOINTS = {
    "ATP": "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard",
    "WTA": "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard",
}

# ESPN doesn't expose a dedicated Challenger tour endpoint; try ATP first —
# some Challenger events surface there, many don't. A None means "leave
# ungraded" rather than auto_win.
TENNIS_LEAGUE_FALLBACKS = {"CHALLENGER": "ATP"}

UNSUPPORTED_LEAGUES = {"Soccer", "UFC", "Boxing"}


@dataclass
class GameResult:
    home_team: str
    away_team: str
    home_score: float
    away_score: float
    is_final: bool


@dataclass
class TennisMatch:
    player1: str
    player2: str
    player1_winner: bool  # meaningful only when is_final
    is_final: bool
    match_date: str  # ISO date, e.g. "2026-04-14"


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

                game = GameResult(
                    home_team=names.get("home", ""),
                    away_team=names.get("away", ""),
                    home_score=scores.get("home", 0),
                    away_score=scores.get("away", 0),
                    is_final=is_final,
                )
                games.append(game)
            except (KeyError, IndexError, ValueError):
                continue

    return games


async def fetch_tennis_matches(league: str, date: datetime) -> List[TennisMatch]:
    """
    Fetch tennis matches for a league around a given date. The tennis scoreboard
    returns whole active tournaments regardless of the single date queried, so
    a match from days earlier in the tournament is reachable even if the pick
    is uploaded later. Doubles matches (competitors without an `athlete` field)
    are skipped.
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
                    # Skip doubles and any match with missing athlete info.
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


def find_matching_tennis_match(
    matches: List[TennisMatch], player_name: str
) -> Optional[TennisMatch]:
    """Match pick player to a tennis match by substring on last name or full token."""
    if not player_name:
        return None
    needle = player_name.lower().strip()
    tokens = [t for t in needle.split() if len(t) > 2]
    for match in matches:
        p1 = match.player1.lower()
        p2 = match.player2.lower()
        if needle and (needle in p1 or needle in p2):
            return match
        # Fall back to per-token substring (covers OCR'd last-name-only picks).
        if tokens and any(t in p1 or t in p2 for t in tokens):
            return match
    return None


def grade_tennis_moneyline(match: TennisMatch, player_name: str) -> str:
    """Grade a tennis moneyline pick. Returns WIN/LOSS."""
    needle = player_name.lower().strip()
    tokens = [t for t in needle.split() if len(t) > 2]
    p1 = match.player1.lower()

    def player1_matches() -> bool:
        if needle and needle in p1:
            return True
        return any(t in p1 for t in tokens)

    picked_player1 = player1_matches()
    picked_winner = match.player1_winner if picked_player1 else (not match.player1_winner)
    return "WIN" if picked_winner else "LOSS"


def find_matching_game(games: List[GameResult], full_team_name: str) -> Optional[GameResult]:
    """Case-insensitive substring match on displayName."""
    if not full_team_name:
        return None
    needle = full_team_name.lower()
    last_word = needle.split()[-1] if needle.split() else ""
    for game in games:
        if needle in game.home_team.lower() or needle in game.away_team.lower():
            return game
        if last_word and len(last_word) > 3:
            if last_word in game.home_team.lower() or last_word in game.away_team.lower():
                return game
    return None


def detect_pick_type(pick_text: str) -> str:
    """Classify pick as spread/moneyline/over/under/prop."""
    text = pick_text.lower()
    if "over" in text:
        return "over"
    if "under" in text:
        return "under"
    if "ml" in text or "moneyline" in text:
        return "moneyline"
    # spread: has a +/- number after team name
    if re.search(r'[+-]\d+\.?\d*', text):
        return "spread"
    # prop: player stat keywords
    if any(kw in text for kw in ["pts", "reb", "ast", "pra", "passing", "rushing", "receiving", "yards", "td"]):
        return "prop"
    return "moneyline"


def extract_team_from_pick_text(pick_text: str) -> Optional[str]:
    """Extract team token from pick text. Returns None for props/totals."""
    pick_type = detect_pick_type(pick_text)
    if pick_type == "prop":
        return None

    text = pick_text.strip()
    # Remove "ML" suffix
    text = re.sub(r'ML\b', '', text, flags=re.IGNORECASE).strip()

    # For over/under with no team: "Over 220.5" → no team
    if pick_type in ("over", "under") and re.match(r'^(over|under)\s+\d', text, re.IGNORECASE):
        return None

    # Extract first word(s) before number/spread
    match = re.match(r'^([A-Za-z\s]+?)(?:\s+[-+]\d|\s+\d|\s+over|\s+under|$)', text, re.IGNORECASE)
    if match:
        team_token = match.group(1).strip()
        if team_token:
            return team_token
    parts = text.split()
    return parts[0] if parts else None


def _get_team_score(game: GameResult, team_name: str) -> Tuple[float, float]:
    """Returns (pick_team_score, opponent_score)."""
    name_lower = team_name.lower()
    last_word = name_lower.split()[-1] if name_lower.split() else ""

    def matches(full_name: str) -> bool:
        return name_lower in full_name or (last_word and len(last_word) > 3 and last_word in full_name)

    if matches(game.home_team.lower()):
        return game.home_score, game.away_score
    elif matches(game.away_team.lower()):
        return game.away_score, game.home_score
    return game.home_score, game.away_score


def grade_spread(game: GameResult, team_name: str, spread_val: float) -> str:
    """Grade a spread pick. WIN if margin > -spread (covers). PUSH if exact."""
    pick_score, opp_score = _get_team_score(game, team_name)
    margin = pick_score - opp_score
    cover_margin = margin + spread_val
    if abs(cover_margin) < 0.01:
        return "PUSH"
    return "WIN" if cover_margin > 0 else "LOSS"


def grade_moneyline(game: GameResult, team_name: str) -> str:
    """Grade a moneyline pick."""
    pick_score, opp_score = _get_team_score(game, team_name)
    if pick_score > opp_score:
        return "WIN"
    elif pick_score < opp_score:
        return "LOSS"
    return "PUSH"


def grade_over_under(game: GameResult, direction: str, line: float) -> str:
    """Grade an over/under pick."""
    total = game.home_score + game.away_score
    if abs(total - line) < 0.01:
        return "PUSH"
    if direction == "over":
        return "WIN" if total > line else "LOSS"
    else:
        return "WIN" if total < line else "LOSS"


def _extract_spread_value(pick_text: str) -> Optional[float]:
    match = re.search(r'([+-]\d+\.?\d*)', pick_text)
    if match:
        return float(match.group(1))
    return None


def _extract_ou_line(pick_text: str) -> Optional[float]:
    match = re.search(r'(over|under|o|u)\s*(\d+\.?\d*)', pick_text, re.IGNORECASE)
    if match:
        return float(match.group(2))
    return None


async def grade_pick_with_espn(
    pick_text: str,
    league: str,
    pick_date: datetime,
    games_cache: Dict,
) -> Optional[Tuple[str, Optional[datetime]]]:
    """
    Attempt to grade a single pick using ESPN data.
    games_cache is keyed by (league, date_str) → list[GameResult].
    Returns (result, match_date) where result is "WIN"|"LOSS"|"PUSH" and
    match_date is the fixture's scheduled datetime when known (currently only
    populated for tennis). Returns None if the pick can't be graded.
    """
    if not league:
        return None
    league_upper = league.upper()

    # Tennis has its own scoreboard shape (players, not teams) and needs a
    # separate grading path. Only moneyline picks are supported; spreads and
    # totals on tennis require set/game scoring we don't parse yet.
    tennis_endpoint_key = TENNIS_LEAGUE_FALLBACKS.get(league_upper, league_upper)
    if tennis_endpoint_key in TENNIS_ENDPOINTS:
        pick_type = detect_pick_type(pick_text)
        if pick_type != "moneyline":
            return None
        player_token = extract_team_from_pick_text(pick_text)
        if not player_token:
            return None
        date_key = (f"tennis:{tennis_endpoint_key}", pick_date.strftime("%Y%m%d"))
        if date_key not in games_cache:
            games_cache[date_key] = await fetch_tennis_matches(league_upper, pick_date)
        matches = games_cache[date_key]
        if not matches:
            return None
        match = find_matching_tennis_match(matches, player_token)
        if match is None or not match.is_final:
            return None
        result = grade_tennis_moneyline(match, player_token)
        match_date: Optional[datetime] = None
        if match.match_date:
            try:
                match_date = datetime.strptime(match.match_date, "%Y-%m-%d")
            except ValueError:
                match_date = None
        return result, match_date

    if league_upper not in ESPN_ENDPOINTS:
        return None

    date_key = (league_upper, pick_date.strftime("%Y%m%d"))

    if date_key not in games_cache:
        games_cache[date_key] = await fetch_scoreboard(league_upper, pick_date)

    games = games_cache[date_key]
    if not games:
        return None

    pick_type = detect_pick_type(pick_text)
    team_token = extract_team_from_pick_text(pick_text)

    if pick_type in ("over", "under"):
        if team_token:
            # Try to look up full team name
            try:
                from ..ocr.teams import get_full_team_name
                full_name = get_full_team_name(team_token) or team_token
            except Exception:
                full_name = team_token
            game = find_matching_game(games, full_name)
        else:
            return None
        if game is None or not game.is_final:
            return None
        line = _extract_ou_line(pick_text)
        if line is None:
            return None
        return grade_over_under(game, pick_type, line), None

    if not team_token:
        return None

    try:
        from ..ocr.teams import get_full_team_name
        full_name = get_full_team_name(team_token) or team_token
    except Exception:
        full_name = team_token

    game = find_matching_game(games, full_name)
    if game is None:
        return None
    if not game.is_final:
        return None  # leave PENDING, game not over

    if pick_type == "moneyline":
        return grade_moneyline(game, full_name), None
    elif pick_type == "spread":
        spread_val = _extract_spread_value(pick_text)
        if spread_val is None:
            return None
        return grade_spread(game, full_name, spread_val), None

    return None
