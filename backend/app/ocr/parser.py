import re
from typing import List, Dict, Any, Optional, Tuple
from .teams import detect_league_from_team, get_full_team_name


# Lines that are noise / not picks
# NOTE: POTD is NOT here — it appears at the end of valid pick lines ("Pick of the Day")
SKIP_PATTERNS = re.compile(
    r"(^\d{1,2}[/\.]\d{1,2}[/\.]\d{2,4}$|"
    r"^@|threads only|create thread|bankroll|take them straight|"
    r"has been really|should be really|whole role|this game should|this might|"
    r"give me the|minutes ago|^\s*$)",
    re.IGNORECASE,
)

# Sport header: "NHL: 1 Unit ( 7:30 PM EST )" or "3/11 nba plays"
SPORT_HEADER_RE = re.compile(
    r"^(NHL|NBA|NFL|MLB|NCAAB|NCAAF|ATP|WTA|Soccer|MLS|EPL|UFC|MMA)\s*[:\s].*?(\d+\.?\d*)\s*[Uu]nit",
    re.IGNORECASE,
)
SPORT_HEADER_NO_UNITS_RE = re.compile(
    r"^(?:\d{1,2}/\d{1,2}\s+)?(NHL|NBA|NFL|MLB|NCAAB|NCAAF|ATP|WTA|Soccer|MLS|EPL|UFC|MMA)\s+plays",
    re.IGNORECASE,
)
# "Main Card: NCAAB & NBA"
MAIN_CARD_RE = re.compile(
    r"Main Card[:\s]+([\w\s&]+)",
    re.IGNORECASE,
)


def _clean_team_name(raw: str) -> str:
    """Strip OCR artifacts and emoji residue from team/player names."""
    # Remove leading non-alpha chars (emoji artifacts like \P, >, etc.)
    cleaned = re.sub(r"^[^A-Za-z]+", "", raw)
    # Remove single leading letter followed by space (OCR emoji residue like "P Kevin")
    cleaned = re.sub(r"^[A-Z]\s+(?=[A-Z])", "", cleaned)
    # Remove trailing non-alphanumeric (emoji, punctuation)
    cleaned = re.sub(r"[^A-Za-z0-9)+]+$", "", cleaned)
    return cleaned.strip()


def _extract_odds(text: str) -> Optional[int]:
    """Extract American odds from text like '(-110)' or '-145' or '+106'."""
    m = re.search(r"\(([+-]\d{3,})\)", text)
    if m:
        return int(m.group(1))
    # Standalone odds (3+ digit number with +/-)
    m = re.search(r"(?<!\d)([+-]\d{3,})(?!\d*\s*[uU])", text)
    if m:
        return int(m.group(1))
    return None


def _extract_units(text: str) -> Optional[float]:
    """Extract units from text — tries multiple patterns."""
    # "10u" or "1.5U" anywhere in text
    m = re.search(r"(\d+\.?\d*)\s*[uU](?:\b|$)", text)
    if m:
        return float(m.group(1))
    # "1 Unit" or "2 Units"
    m = re.search(r"(\d+\.?\d*)\s*[Uu]nits?", text)
    if m:
        return float(m.group(1))
    return None


def _extract_opponent(text: str) -> Optional[str]:
    """Extract opponent from 'v.' or 'vs' patterns."""
    m = re.search(r"v[s.]?\s+([A-Za-z][A-Za-z\s]+?)(?:\s+\d|$)", text)
    if m:
        return m.group(1).strip()
    return None


def _detect_sport_from_context(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Try to detect sport from contextual clues in the line."""
    upper = text.upper()
    if "PRA" in upper or "REBOUNDS" in upper or "POINTS" in upper or "ASSISTS" in upper:
        return "NBA", "Basketball"
    if "RUSHING" in upper or "PASSING" in upper or "RECEIVING" in upper:
        return "NFL", "Football"
    if "STRIKEOUTS" in upper or "HITS" in upper or "ERA" in upper:
        return "MLB", "Baseball"
    return None, None


def parse_picks(raw_text: str) -> List[Dict[str, Any]]:
    """
    Parse raw OCR text into structured picks.
    Handles various formats from real Telegram capper screenshots.
    """
    picks = []
    lines = raw_text.split('\n')

    # Context tracking — sport headers set these for subsequent lines
    ctx_sport = None
    ctx_league = None
    ctx_units = None

    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue

        # Check for sport header lines (set context, not a pick themselves)
        header = SPORT_HEADER_RE.match(line)
        if header:
            ctx_league = header.group(1).upper()
            ctx_sport = _league_to_sport(ctx_league)
            ctx_units = float(header.group(2))
            continue

        header2 = SPORT_HEADER_NO_UNITS_RE.match(line)
        if header2:
            ctx_league = header2.group(1).upper()
            ctx_sport = _league_to_sport(ctx_league)
            ctx_units = None
            continue

        main_card = MAIN_CARD_RE.match(line)
        if main_card:
            # "Main Card: NCAAB & NBA" — take the first sport as context
            sports_text = main_card.group(1).strip()
            for token in re.split(r"[&,\s]+", sports_text):
                token = token.strip().upper()
                if token and token in _SPORT_MAP:
                    ctx_league = token
                    ctx_sport = _league_to_sport(token)
                    break
            continue

        # Skip noise lines
        if SKIP_PATTERNS.search(line):
            continue

        # Try to parse as a pick
        pick = _try_parse_line(line, ctx_sport, ctx_league, ctx_units)
        if pick:
            picks.append(pick)

    return picks


_SPORT_MAP = {
    "NBA": "Basketball",
    "NCAAB": "Basketball",
    "NFL": "Football",
    "NCAAF": "Football",
    "MLB": "Baseball",
    "NHL": "Hockey",
    "ATP": "Tennis",
    "WTA": "Tennis",
    "SOCCER": "Soccer",
    "MLS": "Soccer",
    "EPL": "Soccer",
    "UFC": "MMA",
    "MMA": "MMA",
}


def _league_to_sport(league: str) -> str:
    return _SPORT_MAP.get(league.upper(), "Unknown")


# --- Individual line parsers, tried in order ---

# Format: "Indiana -6.5 (-110) v. Northwestern 10u"
_SPREAD_VS_RE = re.compile(
    r"^(.+?)\s*([+-]\d+\.?\d*)\s*(?:\([+-]?\d+\))?\s*v[s.]?\s+(.+?)(?:\s+(\d+\.?\d*)\s*[uU])?\s*(?:POTD)?$",
    re.IGNORECASE,
)

# Format: "Player O34.5 PRA -110 1u" or "Player O11.5 Rebounds +106 1u"
# Also handles OCR misreading "O" as "0" (zero): "Player 034.5 PRA -110 1u"
_PLAYER_PROP_RE = re.compile(
    r"^(.+?)\s+[OoUu0](\d+\.?\d*)\s+(PRA|Points|Rebounds|Assists|Pts|Reb|Ast|Stl|Blk|Steals|Blocks|Strikeouts|Hits|RBI|Rushing|Passing|Receiving|\w+)(?:\s+([+-]\d+))?\s+(\d+\.?\d*)\s*[uU]",
    re.IGNORECASE,
)

# Format: "Zverev + Alcaraz -145 10U MAX" (team/player spread odds units)
_SPREAD_ODDS_UNITS_RE = re.compile(
    r"^(.+?)\s+([+-]\d+\.?\d*)\s+(\d+\.?\d*)\s*[uU]",
)

# Format: "ChiefsML 1.5u" or "Chiefs ML 1.5u"
_MONEYLINE_UNITS_RE = re.compile(
    r"^(.+?)\s*ML\s+(\d+\.?\d*)\s*[uU]",
    re.IGNORECASE,
)

# Format: "Capitals Moneyline" or "Clippers Moneyline" (no units — from context)
_MONEYLINE_WORD_RE = re.compile(
    r"^(.+?)\s+Moneyline$",
    re.IGNORECASE,
)

# Format: "Over 225.5 3u" or "Under 143"
_OVER_UNDER_RE = re.compile(
    r"^(.*?)\s*(Over|Under)\s+(\d+\.?\d*)(?:\s+(\d+\.?\d*)\s*[uU])?",
    re.IGNORECASE,
)

# Format: "Lakers -5.5 2u"
_SIMPLE_SPREAD_RE = re.compile(
    r"^(.+?)\s*([+-]\d+\.?\d*)\s+(\d+\.?\d*)\s*[uU]",
)

# Format: "Nuggets -5 Alternate Line" or "Team -3.5" — spread without units (uses context)
_SPREAD_NO_UNITS_RE = re.compile(
    r"^([A-Za-z][A-Za-z\s]*?)\s+([+-]\d+\.?\d*)(?:\s|$)",
)

# Format: "(LAKERS -3.5)" — no units
_PARENS_RE = re.compile(
    r"\(?\s*([A-Z][A-Za-z\s]+?)\s*([+-]\d+\.?\d*)\s*\)?$",
)


def _try_parse_line(
    line: str,
    ctx_sport: Optional[str],
    ctx_league: Optional[str],
    ctx_units: Optional[float],
) -> Optional[Dict[str, Any]]:
    """Try all patterns against a single line. Returns a pick dict or None."""

    odds = _extract_odds(line)

    # 1) Spread with opponent: "Indiana -6.5 (-110) v. Northwestern 10u"
    m = _SPREAD_VS_RE.match(line)
    if m:
        team = _clean_team_name(m.group(1))
        spread = m.group(2)
        opponent = m.group(3).strip() if m.group(3) else None
        units = float(m.group(4)) if m.group(4) else (ctx_units or 1.0)
        # Clean opponent trailing junk
        if opponent:
            opponent = re.sub(r"\s*\d+\s*[uU].*$", "", opponent).strip()
        match_key = f"{team} v. {opponent}" if opponent else None
        pick_text = f"{team} {spread}"

        league, sport = detect_league_from_team(team)
        if not league and opponent:
            league, sport = detect_league_from_team(opponent)
        if not sport:
            sport = ctx_sport
            league = league or ctx_league
        full = get_full_team_name(team)

        return _make_pick(pick_text, units, line, sport, league, match_key, full or team, odds)

    # 2) Player prop: "Kevin Durant O34.5 PRA -110 1u"
    m = _PLAYER_PROP_RE.match(line)
    if m:
        player = _clean_team_name(m.group(1))
        value = m.group(2)
        stat = m.group(3)
        prop_odds = int(m.group(4)) if m.group(4) else odds
        units = float(m.group(5))
        pick_text = f"{player} O{value} {stat}"
        league, sport = _detect_sport_from_context(line)
        if not sport:
            sport = ctx_sport
            league = league or ctx_league

        return _make_pick(pick_text, units, line, sport, league, None, player, prop_odds)

    # 3) Moneyline with units: "ChiefsML 1.5u"
    m = _MONEYLINE_UNITS_RE.match(line)
    if m:
        team = _clean_team_name(m.group(1))
        units = float(m.group(2))
        pick_text = f"{team} ML"
        league, sport = detect_league_from_team(team)
        if not sport:
            sport = ctx_sport
            league = league or ctx_league
        full = get_full_team_name(team)

        return _make_pick(pick_text, units, line, sport, league, None, full or team, odds)

    # 4) Moneyline full word: "Capitals Moneyline"
    m = _MONEYLINE_WORD_RE.match(line)
    if m:
        team = _clean_team_name(m.group(1))
        units = ctx_units or 1.0
        pick_text = f"{team} ML"
        league, sport = detect_league_from_team(team)
        if not sport:
            sport = ctx_sport
            league = league or ctx_league
        full = get_full_team_name(team)

        return _make_pick(pick_text, units, line, sport, league, None, full or team, odds)

    # 5) Over/Under: "Clemson/Wake Forest Under 143" or "Over 225.5 3u"
    m = _OVER_UNDER_RE.match(line)
    if m:
        prefix = _clean_team_name(m.group(1)) if m.group(1) else ""
        direction = m.group(2)
        value = m.group(3)
        units = float(m.group(4)) if m.group(4) else (ctx_units or 1.0)
        pick_text = f"{prefix} {direction} {value}".strip() if prefix else f"{direction} {value}"
        match_key = prefix if prefix else None
        # Try to detect sport from prefix teams
        league, sport = None, None
        if prefix:
            for part in re.split(r"[/\s]+", prefix):
                league, sport = detect_league_from_team(part)
                if league:
                    break
        if not sport:
            sport = ctx_sport
            league = league or ctx_league

        return _make_pick(pick_text, units, line, sport, league, match_key, prefix or direction, odds)

    # 6) Simple spread with units: "Lakers -5.5 2u" / "Zverev + Alcaraz -145 10U MAX"
    m = _SIMPLE_SPREAD_RE.match(line)
    if m:
        team = _clean_team_name(m.group(1))
        spread = m.group(2)
        units = float(m.group(3))
        pick_text = f"{team} {spread}"
        league, sport = detect_league_from_team(team)
        if not sport:
            sport = ctx_sport
            league = league or ctx_league
        full = get_full_team_name(team)

        return _make_pick(pick_text, units, line, sport, league, None, full or team, odds)

    # 7) Parenthetical: "(LAKERS -3.5)"
    m = _PARENS_RE.search(line)
    if m:
        team = _clean_team_name(m.group(1))
        spread = m.group(2)
        pick_text = f"{team} {spread}"
        league, sport = detect_league_from_team(team)
        if not sport:
            sport = ctx_sport
            league = league or ctx_league
        full = get_full_team_name(team)

        return _make_pick(pick_text, ctx_units or 1.0, line, sport, league, None, full or team, odds)

    # 8) Spread without units: "Nuggets -5 Alternate Line" (uses context units)
    m = _SPREAD_NO_UNITS_RE.match(line)
    if m:
        team = _clean_team_name(m.group(1))
        spread = m.group(2)
        # Only accept if the team name looks like a real team (not noise)
        league, sport = detect_league_from_team(team)
        if league or ctx_sport:
            pick_text = f"{team} {spread}"
            if not sport:
                sport = ctx_sport
                league = league or ctx_league
            full = get_full_team_name(team)
            return _make_pick(pick_text, ctx_units or 1.0, line, sport, league, None, full or team, odds)

    return None


def _make_pick(
    pick_text: str,
    units: float,
    raw_text: str,
    sport: Optional[str],
    league: Optional[str],
    match_key: Optional[str],
    team_name: str,
    odds: Optional[int] = None,
) -> Dict[str, Any]:
    result = {
        "pick_text": pick_text,
        "units_risked": units,
        "raw_text": raw_text,
        "sport": sport or "Unknown",
        "league": league,
        "match_key": match_key,
        "team_name": team_name,
    }
    if odds is not None:
        result["odds"] = odds
    return result
