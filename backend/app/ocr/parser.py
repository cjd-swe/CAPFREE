import re
from typing import List, Dict, Any, Optional, Tuple
from .teams import detect_league_from_team, get_full_team_name


# ── Capper name extraction ─────────────────────────────────────

# Lines to skip when hunting for a capper name
_CAPPER_SKIP_RE = re.compile(
    r"(^\d{1,2}\s+\w+\s+\d{4}$"          # "11 March 2026"
    r"|^\d{1,2}[/\.]\d{1,2}"              # "3/11" date prefix
    r"|^@cappers"                          # @cappersfree watermarks
    r"|minutes ago|hours ago"             # relative timestamps
    r"|threads only|create thread"        # Telegram UI chrome
    r"|^\s*$)",                            # blank
    re.IGNORECASE,
)

# Tokens that are obviously not capper names
_NOT_A_NAME_RE = re.compile(
    r"^(ATP|NBA|NFL|NHL|MLB|NCAAB|VIP|POTD|MAX|EST|PM|AM|@\w+)$",
    re.IGNORECASE,
)

# Looks like a time: "2:30PM", "10:00 PM EST"
_TIMESTAMP_RE = re.compile(r"\d{1,2}:\d{2}", re.IGNORECASE)


def extract_capper_name(raw_text: str) -> Optional[str]:
    """
    Try to extract the capper's name from the first few lines of OCR text.
    Capper names appear at the top of Telegram screenshots — typically the
    sender's display name — before any pick content.

    Returns the best candidate string, or None if nothing looks reliable.
    """
    lines = raw_text.split('\n')

    for line in lines[:10]:   # only look at the top of the image
        line = line.strip()
        if not line or len(line) < 2:
            continue
        if _CAPPER_SKIP_RE.search(line):
            continue
        if _TIMESTAMP_RE.search(line):
            # Strip the timestamp portion and keep only the name part
            line = _TIMESTAMP_RE.split(line)[0].strip()
            if not line:
                continue

        # Strip leading OCR artifacts (icons, symbols)
        cleaned = re.sub(r"^[^A-Za-z0-9]+", "", line)
        # Strip everything after a # tag or trailing symbols
        cleaned = re.sub(r"\s*#\w+.*$", "", cleaned).strip()
        # Strip trailing non-alphanumeric
        cleaned = re.sub(r"[^A-Za-z0-9]+$", "", cleaned).strip()

        if not cleaned or len(cleaned) < 2:
            continue

        # Try each token in the line — return the first one that looks like a name
        for token in cleaned.split():
            # Skip single characters and purely numeric tokens
            if len(token) < 2 or token.isdigit():
                continue
            # Skip known non-name tokens (league names, VIP, etc.)
            if _NOT_A_NAME_RE.match(token):
                continue
            # Skip 2-letter all-caps tokens — likely icon/badge artifacts (e.g. "AC", "YD")
            if len(token) == 2 and token.isupper():
                continue

            return token

    return None


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

# Bare "Tennis" header (emoji/OCR garbage allowed after): sets sport, leaves
# league open for a more specific tournament header to follow.
TENNIS_SPORT_HEADER_RE = re.compile(r"^Tennis\b", re.IGNORECASE)

# Tennis tournament header: "ATP Barcelona", "WTA Rouen", "Challenger Oeiras",
# "ATP Monte Carlo". City name, no digits/odds/units — headers stand alone on
# their own line.
TENNIS_TOURNAMENT_HEADER_RE = re.compile(
    r"^(ATP|WTA|Challenger)\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*$",
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
    # "1 Unit", "2 Units", "(2 units)", "(2 unit)"
    m = re.search(r"\(?\s*(\d+\.?\d*)\s*[Uu]nits?\s*\)?", text)
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


# ── Bet slip detection & parsing ──────────────────────────────────────────────

# Signals that the image is a sportsbook bet slip receipt
_BET_SLIP_SIGNALS = re.compile(
    r"straights?\s*\(\d+\)|bet has been accepted|share my bet|"
    r"keep placed bets|total payout|your bets?\s+(?:is|are)\s+confirmed|"
    r"wager\s+\$|bet\s+confirmed|bet slip|betslip",
    re.IGNORECASE,
)

# OCR misreads "-" as '"' or "'" before 3-4 digit odds
_ODDS_ARTIFACT_RE = re.compile(r'["\'\u201c\u201d](\d{3,4})')

# Match line inside a bet slip: "Team at Opponent" or "Team vs Opponent"
_MATCH_LINE_RE = re.compile(
    r"^(.+?)\s+(?:at|@|vs\.?)\s+(.+?)(?:\s*\(.*\))?$",
    re.IGNORECASE,
)

# Bet slip pick line: "Team -3.5 [Spread] -110" or "Team ML +150"
_SLIP_PICK_RE = re.compile(
    r"^(.+?)\s+([+-]\d+\.?\d*)\s*(?:ML|Moneyline)?\s*(?:[+-]\d{3,4})?",
    re.IGNORECASE,
)


def _normalize_slip_text(text: str) -> str:
    """Fix common OCR artifacts in bet slip screenshots."""
    # '"110' or '\u201c110' → '-110' (OCR misreads minus as quote before odds)
    return _ODDS_ARTIFACT_RE.sub(r"-\1", text)


def _parse_as_bet_slip(raw_text: str) -> List[Dict[str, Any]]:
    """
    Parse a sportsbook bet slip screenshot.
    Extracts pick(s) from the structured receipt format used by
    DraftKings, FanDuel, BetMGM, Caesars, etc.
    """
    text = _normalize_slip_text(raw_text)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    picks = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Find the Straights section or pick lines with spread/ML
        # Look for a line with a spread/ML value that's likely a pick
        pick_m = re.match(
            r"^([A-Za-z][A-Za-z\s\.\-']+?)\s+([+-]\d+\.?\d*)",
            line,
        )
        if pick_m:
            team_raw = pick_m.group(1).strip()
            spread = pick_m.group(2)

            # Skip noise lines (short words, known UI text)
            skip_words = {"spread", "moneyline", "total", "over", "under",
                          "stake", "payout", "straights", "parlays", "share",
                          "keep", "your", "bet", "slip", "confirmed"}
            if team_raw.lower() in skip_words or len(team_raw) < 2:
                i += 1
                continue

            # Extract odds — search up to 6 lines ahead (bet slips often have
            # odds on a separate line after the pick)
            odds = _extract_odds(line)
            for j in range(i + 1, min(i + 7, len(lines))):
                if odds is not None:
                    break
                odds = _extract_odds(lines[j])

            # Look ahead for a match line ("Team at Opponent") — validate that
            # both sides look like proper team names (not phrases like "See you at the window")
            match_key = None
            for j in range(i + 1, min(i + 6, len(lines))):
                mm = _MATCH_LINE_RE.match(lines[j])
                if mm:
                    home = mm.group(1).strip()
                    away = mm.group(2).strip()
                    # Reject if either side is a short common phrase or > 4 words
                    home_words = home.split()
                    away_words = away.split()
                    if (len(home_words) > 4 or len(away_words) > 4):
                        continue
                    # Reject common false positives
                    false_pos = {"see", "you", "look", "come", "meet"}
                    if home_words[0].lower() in false_pos:
                        continue
                    # Prefer lines where at least one side is a known team
                    home_l, _ = detect_league_from_team(home)
                    away_l, _ = detect_league_from_team(away)
                    if home_l or away_l:
                        match_key = f"{home} vs {away}"
                        break
                    # Accept even unknown teams if both words are capitalised
                    if home[0].isupper() and away[0].isupper():
                        match_key = f"{home} vs {away}"
                        break

            # Extract units from earlier lines (capper usually puts "2 units" in caption)
            units = _extract_units(raw_text) or 1.0

            team = _clean_team_name(team_raw)
            league, sport = detect_league_from_team(team)
            # Try match teams if we got one
            if not league and match_key:
                for part in re.split(r"\s+(?:vs|at|@)\s+", match_key):
                    league, sport = detect_league_from_team(part.strip())
                    if league:
                        break
            full = get_full_team_name(team)
            pick_text = f"{team} {spread}"

            picks.append(_make_pick(
                pick_text, units, line, sport, league, match_key,
                full or team, odds,
            ))

        i += 1

    # Deduplicate — bet slips often repeat the pick in summary
    seen: set = set()
    deduped = []
    for p in picks:
        key = p["pick_text"].lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    return deduped


def parse_picks(raw_text: str) -> List[Dict[str, Any]]:
    """
    Parse raw OCR text into structured picks.
    Handles various formats from real Telegram capper screenshots.
    """
    # Fast-path: if this looks like a sportsbook bet slip, use the slip parser
    if _BET_SLIP_SIGNALS.search(raw_text):
        slip_picks = _parse_as_bet_slip(raw_text)
        if slip_picks:
            return slip_picks

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

        # Tennis tournament header (check before bare "Tennis" so a line like
        # "ATP Barcelona" wins over any generic tennis match).
        tennis_tourney = TENNIS_TOURNAMENT_HEADER_RE.match(line)
        if tennis_tourney:
            ctx_league = tennis_tourney.group(1).upper()
            ctx_sport = "Tennis"
            ctx_units = None
            continue

        if TENNIS_SPORT_HEADER_RE.match(line):
            ctx_sport = "Tennis"
            # Don't clobber a more specific league if we somehow already have one
            ctx_units = None
            continue

        # Skip noise lines
        if SKIP_PATTERNS.search(line):
            continue

        # Try to parse as a pick
        pick = _try_parse_line(line, ctx_sport, ctx_league, ctx_units)
        if pick:
            picks.append(pick)

    # Deduplicate: prefer picks with a known team_name (full name) over raw OCR variants.
    # Key on (normalized_full_team_name, spread/odds) so "Boston Univ -128" and
    # "Boston University -128" collapse to one entry.
    seen: set = set()
    deduped = []
    for p in picks:
        # Use the resolved full team name if available, else fall back to pick_text
        team_key = (p.get("team_name") or p["pick_text"]).lower().strip()
        # Extract the numeric part of the pick (spread or odds) for the key
        num_match = re.search(r"[+-]\d+\.?\d*", p["pick_text"])
        num_part = num_match.group(0) if num_match else ""
        key = f"{team_key}|{num_part}"
        if key not in seen:
            seen.add(key)
            deduped.append(p)

    return deduped


_SPORT_MAP = {
    "NBA": "Basketball",
    "NCAAB": "Basketball",
    "NFL": "Football",
    "NCAAF": "Football",
    "MLB": "Baseball",
    "NHL": "Hockey",
    "ATP": "Tennis",
    "WTA": "Tennis",
    "CHALLENGER": "Tennis",
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

# Game time pattern to strip from pick lines: "6:30pm", "9:30pm", "7pm", "10:00 PM EST"
_GAME_TIME_RE = re.compile(r"\s+\d{1,2}(?::\d{2})?\s*[apAP][mM](?:\s*EST|PST|CST|MST)?", re.IGNORECASE)
# Star rating chars
_STARS_RE = re.compile(r"[\u2605\u2606\u2b50\*]{1,5}")


def _preclean_line(line: str) -> str:
    """Strip leading symbols, game times, and star ratings from a pick line."""
    cleaned = re.sub(r"^[^A-Za-z0-9(]+", "", line)
    cleaned = _GAME_TIME_RE.sub("", cleaned)
    cleaned = _STARS_RE.sub("", cleaned)
    return cleaned.strip()


# Format: "Marquette (NCAAB) 1" — sharp plays with league in parens and N units
_SHARP_PLAYS_RE = re.compile(
    r"^(.+?)\s+\((NBA|NFL|NHL|MLB|NCAAB|NCAAF|ATP|MLS|EPL|UFC|MMA)\)\s+(\d+)$",
    re.IGNORECASE,
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

    # Pre-clean: strip leading symbols and trailing game times/stars
    line = _preclean_line(line)
    if not line:
        return None

    odds = _extract_odds(line)

    # 0) Sharp plays format: "Marquette (NCAAB) 1" — team (league) N units
    m = _SHARP_PLAYS_RE.match(line)
    if m:
        team = _clean_team_name(m.group(1))
        league = m.group(2).upper()
        units = float(m.group(3))
        sport = _league_to_sport(league)
        pick_text = f"{team} (sharp play)"
        full = get_full_team_name(team)
        return _make_pick(pick_text, units, line, sport, league, None, full or team, odds)

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
        # Reject if prefix looks like a sentence fragment (too many words or too long)
        if prefix and (len(prefix.split()) > 6 or len(prefix) > 50):
            return None
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

    # 8) Spread without units: "Nuggets -5 Alternate Line" or "BYU -3.5 (2 units)"
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
            # Try to extract units from the rest of the line before falling back to context
            line_units = _extract_units(line)
            return _make_pick(pick_text, line_units or ctx_units or 1.0, line, sport, league, None, full or team, odds)

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
