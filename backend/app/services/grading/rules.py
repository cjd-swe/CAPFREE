from datetime import datetime
from typing import Optional, List, Tuple

from .types import GameResult, TennisMatch
from .pick_text import (
    detect_pick_type,
    extract_team_from_pick_text,
    parse_doubles_names,
    _extract_spread_value,
    _extract_ou_line,
)


def _to_dt(iso: str) -> Optional[datetime]:
    if not iso:
        return None
    try:
        return datetime.strptime(iso, "%Y-%m-%d")
    except ValueError:
        return None


# ─── Team matching ───────────────────────────────────────────────────────────

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


# ─── Team grading ────────────────────────────────────────────────────────────

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


# ─── Tennis matching ─────────────────────────────────────────────────────────

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
        if tokens and any(t in p1 or t in p2 for t in tokens):
            return match
    return None


def find_doubles_match(
    matches: List[TennisMatch], partner_tokens: List[str]
) -> Optional[TennisMatch]:
    """Find a doubles match where one team's combined name contains BOTH tokens."""
    if not partner_tokens or len(partner_tokens) < 2:
        return None
    tokens = [t for t in partner_tokens if len(t) > 2]
    if len(tokens) < 2:
        return None
    for m in matches:
        for side in (m.player1, m.player2):
            side_lower = side.lower()
            if all(t in side_lower for t in tokens):
                return m
    return None


# ─── Tennis grading ──────────────────────────────────────────────────────────

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


def doubles_team_won(match: TennisMatch, partner_tokens: List[str]) -> bool:
    """Return True if the picked doubles pair won. Caller must confirm match.is_final."""
    tokens = [t for t in partner_tokens if len(t) > 2]
    p1_lower = match.player1.lower()
    picked_home = all(t in p1_lower for t in tokens)
    return match.player1_winner if picked_home else (not match.player1_winner)


# ─── Dispatch ────────────────────────────────────────────────────────────────

def _grade_team(
    records: List[GameResult], pick_text: str, pick_type: str
) -> Optional[Tuple[str, Optional[datetime]]]:
    if pick_type in ("over", "under"):
        team_token = extract_team_from_pick_text(pick_text)
        if not team_token:
            return None
        try:
            from ...ocr.teams import get_full_team_name
            full_name = get_full_team_name(team_token) or team_token
        except Exception:
            full_name = team_token
        game = find_matching_game(records, full_name)
        if game is None or not game.is_final:
            return None
        line = _extract_ou_line(pick_text)
        if line is None:
            return None
        return grade_over_under(game, pick_type, line), None

    team_token = extract_team_from_pick_text(pick_text)
    if not team_token:
        return None
    try:
        from ...ocr.teams import get_full_team_name
        full_name = get_full_team_name(team_token) or team_token
    except Exception:
        full_name = team_token

    game = find_matching_game(records, full_name)
    if game is None or not game.is_final:
        return None

    if pick_type == "moneyline":
        return grade_moneyline(game, full_name), None
    elif pick_type == "spread":
        spread_val = _extract_spread_value(pick_text)
        if spread_val is None:
            return None
        return grade_spread(game, full_name, spread_val), None

    return None


def _grade_tennis(
    records: List[TennisMatch], pick_text: str, pick_type: str
) -> Optional[Tuple[str, Optional[datetime]]]:
    if pick_type != "moneyline":
        return None

    doubles_tokens = parse_doubles_names(pick_text)
    if doubles_tokens:
        match = find_doubles_match(records, doubles_tokens)
        if match is None or not match.is_final:
            return None
        won = doubles_team_won(match, doubles_tokens)
        return ("WIN" if won else "LOSS"), _to_dt(match.match_date)

    player_token = extract_team_from_pick_text(pick_text)
    if not player_token:
        return None
    match = find_matching_tennis_match(records, player_token)
    if match is None or not match.is_final:
        return None
    return grade_tennis_moneyline(match, player_token), _to_dt(match.match_date)


def grade_records(
    records: list, pick_text: str, pick_type: str
) -> Optional[Tuple[str, Optional[datetime]]]:
    """Dispatch to team or tennis grading based on record type."""
    if not records:
        return None
    if isinstance(records[0], TennisMatch):
        return _grade_tennis(records, pick_text, pick_type)
    return _grade_team(records, pick_text, pick_type)
