"""
Convergence analysis: group picks by game/market across cappers, find consensus
and conflicts. Used by both the daily DB endpoint and the Telegram export upload.
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .grading.pick_text import detect_pick_type, extract_team_from_pick_text, _extract_ou_line
from ..ocr.teams import get_full_team_name, detect_league_from_team

_scoreboard_cache: Dict[Tuple[str, str], List] = {}


def extract_side(pick: Dict[str, Any]) -> Optional[str]:
    pick_text = pick.get("pick_text", "")
    pick_type = detect_pick_type(pick_text)
    if pick_type == "prop":
        return None
    if pick_type in ("over", "under"):
        line = _extract_ou_line(pick_text)
        return f"{pick_type.upper()} {line}" if line is not None else pick_type.upper()
    team_token = extract_team_from_pick_text(pick_text)
    if not team_token:
        return None
    return get_full_team_name(team_token) or team_token


async def resolve_game_key(pick: Dict[str, Any], game_date: datetime) -> Optional[str]:
    from .grading.espn import fetch_scoreboard
    from .grading.rules import find_matching_game

    mk = pick.get("match_key")
    if mk:
        return mk.replace(" vs ", " @ ").replace(" v. ", " @ ")

    pick_text = pick.get("pick_text", "")
    if detect_pick_type(pick_text) == "prop":
        return None

    team_token = extract_team_from_pick_text(pick_text)
    if not team_token:
        return None

    full_name = get_full_team_name(team_token) or team_token
    league = pick.get("league")
    if not league:
        league, _ = detect_league_from_team(team_token)
    if not league:
        return None

    lu = league.upper()
    cache_key = (lu, game_date.strftime("%Y%m%d"))
    if cache_key not in _scoreboard_cache:
        _scoreboard_cache[cache_key] = await fetch_scoreboard(lu, game_date)

    game = find_matching_game(_scoreboard_cache[cache_key], full_name)
    return f"{game.away_team} @ {game.home_team}" if game else None


def compute_convergence(picks: List[Dict[str, Any]]) -> Dict[str, Any]:
    groups: Dict[Tuple[str, str], Dict[str, Set[str]]] = {}
    unmatched: List[Dict[str, Any]] = []

    for p in picks:
        gk = p.get("_game_key")
        side = p.get("_side")
        if not gk or not side:
            unmatched.append(p)
            continue
        market = detect_pick_type(p.get("pick_text", ""))
        key = (gk, market)
        groups.setdefault(key, {})
        capper = p.get("_capper") or "unknown"
        groups[key].setdefault(side, set()).add(capper)

    consensus: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []

    for (game_key, market), sides in groups.items():
        all_cappers: Set[str] = set()
        for s in sides.values():
            all_cappers |= s
        total = len(all_cappers)
        if total < 2:
            continue

        sorted_sides = sorted(sides.items(), key=lambda x: len(x[1]), reverse=True)
        dom_side, dom_cappers = sorted_sides[0]
        dom_count = len(dom_cappers)

        entry: Dict[str, Any] = {
            "game": game_key,
            "market": market,
            "total_cappers": total,
            "sides": {s: sorted(c) for s, c in sorted_sides},
            "dominant_side": dom_side,
            "dominant_count": dom_count,
            "share_pct": round(dom_count / total * 100, 1),
        }

        if len(sorted_sides) > 1 and len(sorted_sides[1][1]) >= 2:
            entry["conflict_side"] = sorted_sides[1][0]
            entry["conflict_count"] = len(sorted_sides[1][1])
            conflicts.append(entry)
        elif dom_count >= 3:
            consensus.append(entry)
        elif dom_count == 2:
            entry["note"] = "only 2 cappers — low confidence"
            consensus.append(entry)

    consensus.sort(key=lambda x: (-x["dominant_count"], -x["share_pct"]))
    conflicts.sort(key=lambda x: -x["total_cappers"])
    return {"consensus": consensus, "conflicts": conflicts, "unmatched": unmatched}
