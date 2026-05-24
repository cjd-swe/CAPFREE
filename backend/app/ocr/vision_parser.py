"""
Claude Haiku vision fallback for pick parsing.

Called only when OCR+regex produces an unreliable result (0 picks, garbage
text, or all picks missing units+odds+sport). Returns the same pick dict
shape as parser.parse_picks so downstream code is unchanged.
"""
import base64
import json
import logging
import re
from typing import Any, Dict, List, Optional

import anthropic

from ..config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a sports betting pick extractor. You receive screenshots from Telegram \
groups where sports handicappers ("cappers") post their picks. Your job is to \
read the screenshot and extract structured data.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON, no markdown fences, no commentary:

{
  "capper_name": string | null,
  "picks": [
    {
      "pick_text": string,
      "units_risked": number,
      "sport": string,
      "league": string | null,
      "match_key": string | null,
      "odds": integer | null
    }
  ]
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPPER NAME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The capper's name usually appears at the very top of the screenshot as the
Telegram sender's display name. It may be followed by a checkmark, emoji,
or timestamp. Return just the name, stripped of symbols. If no name is
visible or it is ambiguous, return null.

Examples of capper name lines:
  "SharpBets_Official ✓"  → "SharpBets_Official"
  "BestCappers 2:34 PM"   → "BestCappers"
  "@cappersfree"          → null  (watermark, not a real sender name)
  "3/11 NBA Plays"        → null  (date header, not a name)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PICK FORMATS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cappers write picks in many formats. Here are the main patterns:

1. SPREAD WITH UNITS
   "Lakers -5.5 2u"         → pick_text="Lakers -5.5", units=2.0
   "Bills -3 (-110) 3u"     → pick_text="Bills -3", odds=-110, units=3.0
   "Indiana -6.5 v. Northwestern 10u" → pick_text="Indiana -6.5", match_key="Indiana v. Northwestern"

2. MONEYLINE
   "Chiefs ML 1.5u"         → pick_text="Chiefs ML", units=1.5
   "Pacers Moneyline"       → pick_text="Pacers ML", units=1.0 (from context or default)
   "Warriors +145 2u"       → pick_text="Warriors +145", units=2.0, odds=145

3. PLAYER PROPS
   "Kevin Durant O34.5 PRA -110 1u"  → pick_text="Kevin Durant O34.5 PRA", odds=-110, units=1.0
   "Curry U28.5 Points 2u"           → pick_text="Curry U28.5 Points", units=2.0
   "Mahomes O275.5 Passing Yards +105 1u" → pick_text="Mahomes O275.5 Passing Yards", odds=105

4. TOTALS (OVER/UNDER)
   "Over 225.5 3u"                      → pick_text="Over 225.5", units=3.0
   "Celtics/Heat Under 215 2u"          → pick_text="Celtics/Heat Under 215", units=2.0
   "Cubs/Cardinals Over 8.5 (-115) 1u"  → pick_text="Cubs/Cardinals Over 8.5", odds=-115, units=1.0

5. SHARP PLAYS FORMAT
   "Marquette (NCAAB) 3"    → pick_text="Marquette (sharp play)", units=3.0, league="NCAAB"
   "Celtics (NBA) 2"        → pick_text="Celtics (sharp play)", units=2.0, league="NBA"

6. PARENTHETICAL FORMAT
   "(LAKERS -3.5)"          → pick_text="LAKERS -3.5"

7. "TEAM (VALUE) over OPPONENT" FORMAT — common in Telegram posts
   The word "over" here means "versus the opponent", NOT an over/under total.
   Small value (abs < 50) = spread. Large value (abs ≥ 50) = moneyline odds.

   "NY KNICKS (+2.5) over Cleveland Cavs (4-UNITS)"
     → pick_text="NY KNICKS +2.5", units=4.0, sport="Basketball", league="NBA",
       match_key="NY KNICKS v. Cleveland Cavs"

   "CHICAGO WHITE SOX (+102) over SF Giants (+3-UNITS)"
     → pick_text="CHICAGO WHITE SOX ML", odds=102, units=3.0, sport="Baseball", league="MLB",
       match_key="CHICAGO WHITE SOX v. SF Giants"

   "ATHLETICS (-110) over San Diego Padres (4-UNITS)"
     → pick_text="ATHLETICS ML", odds=-110, units=4.0, sport="Baseball", league="MLB"

8. SPLIT MATCHUP + PICK FORMAT — matchup on one line, bet on the next
   "KNICKS/CAVS"            (matchup line — context for what follows)
   "OVER 215.5"             → pick_text="KNICKS/CAVS Over 215.5", sport="Basketball", league="NBA"

   "DODGERS/BREWERS"
   "OVER 9 (-105)"          → pick_text="DODGERS/BREWERS Over 9", odds=-105, sport="Baseball", league="MLB"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UNITS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Default units_risked = 1.0 if not specified.
• Units indicators: "1u", "2U", "1.5u", "2 units", "(2 unit)", "10U MAX"
• "(4-UNITS)" or "(+3-UNITS)" with a dash also means 4 or 3 units — very common in Telegram posts.
• If a sport header sets units ("NBA: 2 Units (7:30 PM EST)"), use that for
  all subsequent picks in that section until a new header appears.
• "MAX" or "POTD" after units does not change the unit count.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SPORT HEADERS (context-setting lines, not picks themselves)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Lines like these set the sport/league context for subsequent picks.
Do NOT emit them as picks.

  "NHL: 1 Unit (7:30 PM EST)"   → context: league=NHL, units=1.0
  "3/11 NBA Plays"              → context: league=NBA
  "Main Card: NCAAB & NBA"      → context: league=NCAAB (first listed)
  "ATP Barcelona"               → context: league=ATP, sport=Tennis
  "WTA Rome"                    → context: league=WTA, sport=Tennis
  "Challenger Oeiras"           → context: league=CHALLENGER, sport=Tennis
  "Tennis"                      → context: sport=Tennis

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARLAYS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A parlay header like "Parlay: 1 Unit ( NHL/NBA )" introduces a multi-leg
bet. ALL pick lines that follow it (until the next section header) are legs
of that ONE parlay — not separate standalone picks.

Emit the whole parlay as a SINGLE pick entry:
  • pick_text: "Parlay: <Leg1> + <Leg2> + ..."  (join each leg's description)
  • units_risked: units from the parlay header
  • sport: "Parlay"
  • league: null
  • odds: null (parlay odds usually aren't shown per-leg)

Example:
  "Parlay: 1 Unit ( NHL/NBA )"
  "Hurricanes Moneyline"
  "Cavaliers +10 Alternate Line"

→ ONE pick:
  {"pick_text": "Parlay: Hurricanes ML + Cavaliers +10", "units_risked": 1.0,
   "sport": "Parlay", "league": null, "odds": null, "match_key": null}

Do NOT emit "Hurricanes ML" and "Cavaliers +10" as separate picks — they are
legs of the parlay above, not independent bets.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SPORT VALUES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Map league codes to sport values:
  NBA, NCAAB → "Basketball"
  NFL, NCAAF → "Football"
  MLB        → "Baseball"
  NHL        → "Hockey"
  ATP, WTA, CHALLENGER → "Tennis"
  MLS, EPL, Soccer → "Soccer"
  UFC, MMA   → "MMA"

If no sport can be determined, use "Unknown".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ODDS FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

American odds only. Return as integer:
  "-110" → -110
  "+150" → 150
  "(-115)" → -115 (parenthetical form, common in screenshots)

If no odds are specified, return null for the odds field.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BET SLIP RECEIPTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Some screenshots are sportsbook bet slip receipts (DraftKings, FanDuel,
BetMGM, Caesars, etc.) rather than capper message screenshots. They contain
text like "Bet Confirmed", "Total Payout", "Straights (N)", etc.

For bet slips:
• Extract each bet line (spread, ML, total) as a pick.
• capper_name will be null (the bettor is not identified).
• The match line ("Team A at Team B") provides match_key.
• Units come from the wager amount if visible; else default to 1.0.
• Extract odds from the bet slip line.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT TO SKIP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Skip these — they are noise, not picks:
  • Date lines: "3/11", "March 11", "11 March 2026"
  • Timestamps alone: "2:30 PM EST"
  • Promotional text: "bankroll management", "take them straight", "these are locks"
  • Telegram UI chrome: "Threads only", "Create thread", "X minutes ago"
  • @watermarks: "@cappersfree", "@SharpWatch"
  • Blank lines, separator lines

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PICK_TEXT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pick_text should be clean and concise:
  "Lakers -5.5"              (spread)
  "Chiefs ML"                (moneyline)
  "Celtics/Heat Under 215"   (total)
  "Kevin Durant O34.5 PRA"   (player prop — O/U + stat, no odds in text)
  "Bulls +135"               (positive ML spread)

Do NOT put units or odds inside pick_text. Units go in units_risked;
odds go in the odds field.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MATCH_KEY FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

match_key is optional. Use it when the screenshot clearly shows both teams
in a matchup. Format: "Team A v. Team B" or "Team A vs Team B".
For player props and totals without a listed matchup, use null.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE INPUT → OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Screenshot text (what OCR might produce):
  SharpBets_Official ✓
  3/11 NBA Plays
  Lakers -5.5 2u
  Bucks ML (-130) 1u
  Kevin Durant O34.5 PRA -110 1u

Expected output:
{
  "capper_name": "SharpBets_Official",
  "picks": [
    {"pick_text": "Lakers -5.5", "units_risked": 2.0, "sport": "Basketball", "league": "NBA", "match_key": null, "odds": null},
    {"pick_text": "Bucks ML", "units_risked": 1.0, "sport": "Basketball", "league": "NBA", "match_key": null, "odds": -130},
    {"pick_text": "Kevin Durant O34.5 PRA", "units_risked": 1.0, "sport": "Basketball", "league": "NBA", "match_key": null, "odds": -110}
  ]
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Return ONLY the JSON object. No markdown, no explanation.
2. If no picks are found, return {"capper_name": null, "picks": []}.
3. Never invent picks that are not clearly present in the screenshot.
4. When in doubt about units, default to 1.0.
5. When in doubt about sport, use "Unknown".
6. Odds must be integers (no decimals). If the image shows "-110.5", round.
7. Strip emoji and OCR artifacts from team/player names in pick_text.
"""

_EMPTY: Dict[str, Any] = {"capper_name": None, "picks": []}
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


async def parse_picks_from_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Send image to Claude Haiku and return structured picks.
    Returns _EMPTY on any error — caller falls back to OCR result.
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.debug("ANTHROPIC_API_KEY not set; skipping vision parse")
        return _EMPTY

    media_type = _sniff_media_type(image_bytes)
    b64 = base64.standard_b64encode(image_bytes).decode()

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    try:
        response = await client.messages.create(
            model=settings.VISION_MODEL,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Extract the picks from this screenshot. Return JSON only.",
                        },
                    ],
                }
            ],
        )
    except Exception:
        logger.exception("Vision API call failed")
        return _EMPTY

    try:
        raw = response.content[0].text.strip()
        raw = _CODE_FENCE_RE.sub("", raw).strip()
        data = json.loads(raw)
    except Exception:
        logger.exception("Vision response JSON parse failed")
        return _EMPTY

    picks = _normalize_picks(data.get("picks") or [])
    return {
        "capper_name": data.get("capper_name") or None,
        "picks": picks,
    }


def _normalize_picks(raw_picks: List[Any]) -> List[Dict[str, Any]]:
    out = []
    for p in raw_picks:
        if not isinstance(p, dict):
            continue
        pick_text = (p.get("pick_text") or "").strip()
        if not pick_text:
            continue
        normalized: Dict[str, Any] = {
            "pick_text": pick_text,
            "units_risked": float(p.get("units_risked") or 1.0),
            "sport": p.get("sport") or "Unknown",
            "league": p.get("league") or None,
            "match_key": p.get("match_key") or None,
            "team_name": pick_text,  # best-effort for dedup
        }
        odds = p.get("odds")
        if odds is not None:
            try:
                normalized["odds"] = int(odds)
            except (TypeError, ValueError):
                pass
        out.append(normalized)
    return out


def _sniff_media_type(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"GIF8":
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"
