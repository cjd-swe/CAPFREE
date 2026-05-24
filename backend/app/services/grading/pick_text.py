import re
import unicodedata
from typing import Optional, List

UNSUPPORTED_LEAGUES = {"Soccer", "UFC", "Boxing"}

_DOUBLES_PICK_RE = re.compile(
    r"^\s*([A-Za-z][A-Za-z\-']+)\s*\+\s*([A-Za-z][A-Za-z\-']+)\b",
    re.IGNORECASE,
)


def _ascii_fold(s: str) -> str:
    """Strip diacritics so 'Comesaña' matches 'Comesana'."""
    if not s:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def detect_pick_type(pick_text: str) -> str:
    """Classify pick as spread/moneyline/over/under/prop."""
    text = pick_text.lower()
    if "over" in text:
        return "over"
    if "under" in text:
        return "under"
    if "ml" in text or "moneyline" in text:
        return "moneyline"
    if re.search(r'[+-]\d+\.?\d*', text):
        return "spread"
    if any(kw in text for kw in ["pts", "reb", "ast", "pra", "passing", "rushing", "receiving", "yards", "td"]):
        return "prop"
    return "moneyline"


def extract_team_from_pick_text(pick_text: str) -> Optional[str]:
    """Extract team token from pick text. Returns None for props/totals."""
    pick_type = detect_pick_type(pick_text)
    if pick_type == "prop":
        return None

    text = pick_text.strip()
    text = re.sub(r'ML\b', '', text, flags=re.IGNORECASE).strip()

    if pick_type in ("over", "under") and re.match(r'^(over|under)\s+\d', text, re.IGNORECASE):
        return None

    match = re.match(r'^([A-Za-z\s]+?)(?:\s+[-+]\d|\s+\d|\s+over|\s+under|$)', text, re.IGNORECASE)
    if match:
        team_token = match.group(1).strip()
        if team_token:
            return team_token
    parts = text.split()
    return parts[0] if parts else None


def parse_doubles_names(pick_text: str) -> Optional[List[str]]:
    """
    If pick_text looks like a tennis doubles pick ("Name + Name ..."), return
    the two partner tokens; otherwise None.
    """
    match = _DOUBLES_PICK_RE.match(pick_text or "")
    if not match:
        return None
    return [_ascii_fold(match.group(1)).lower(), _ascii_fold(match.group(2)).lower()]


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
