#!/usr/bin/env python3
"""
convergence_report.py — Telegram export → per-capper results + convergence/conflict analysis

Usage (from repo root):
    PYTHONPATH=venv/lib/python3.8/site-packages python3.8 backend/scripts/convergence_report.py \
        "/path/to/ChatExport_2026-06-22"

Outputs (in the export folder):
    results_YYYYMMDD.csv        — per-capper W/L scorecard decoded from ✅/❌ recap captions
    convergence_YYYYMMDD.md     — consensus plays + conflict games for live picks
    picks_raw_YYYYMMDD.json     — full extracted pick data (debug)

The script forces PARSE_ENGINE=vision so every image goes through Claude Haiku for
reliable structured extraction. Requires ANTHROPIC_API_KEY in backend/.env.
"""
import asyncio
import csv
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─── Path bootstrap (before any app imports) ──────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = REPO_ROOT / "backend"
VENV_SITE = REPO_ROOT / "venv" / "lib" / "python3.8" / "site-packages"

for p in [str(VENV_SITE), str(BACKEND)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Load .env before importing any app modules (settings is a global at import time)
_env_file = BACKEND / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v

# Force vision mode before config is imported
os.environ["PARSE_ENGINE"] = "vision"

# Provide dummy DB URL so config doesn't raise on missing required field
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://dummy:dummy@localhost/dummy"

# ─── App imports (order matters: env vars must be set first) ──────────────────
from app.ocr import parse_router                          # noqa: E402
from app.ocr.teams import get_full_team_name, detect_league_from_team  # noqa: E402
from app.services.grading.espn import fetch_scoreboard   # noqa: E402
from app.services.grading.rules import find_matching_game  # noqa: E402
from app.services.grading.pick_text import (             # noqa: E402
    detect_pick_type,
    extract_team_from_pick_text,
    _extract_spread_value,
    _extract_ou_line,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────
WIN_EMOJI = "✅"
LOSS_EMOJI = "❌"
PUSH_EMOJI = "⬛"

PROMO_PATTERNS = re.compile(
    r"cheapest|prices in the industry|join the best|bankroll|"
    r"guarantee:|bonus capper|for any question|reach out|"
    r"everyone'?s favorite|exclusive play|seeking returns|"
    r"really the|pay per view|ppv|subscribe|follow us|sign up|\bfree\b.*trial|"
    r"\bbankroll\b(?!\w)|cheapest prices",
    re.IGNORECASE,
)

# Promo words that are suspicious ONLY when they dominate (no real capper name remains after noise-strip)
_PROMO_FALLBACK = re.compile(
    r"^(?:join|cheapest|best team|bonus|dmonly|team|owner|everyone|guarantee)",
    re.IGNORECASE,
)

RESULT_RE = re.compile(r"[✅❌⬛]")
# Capper attribution with trailing result emoji e.g. "JS - ✅" or "LAFORMULA - ✅✅"
RECAP_RE = re.compile(r"^(.+?)(?:\s*[-–—]\s*)?([✅❌⬛]+)\s*$")

# Channel watermark noise (mirrors parse_router._CAPPER_NOISE_RE)
_NOISE_RE = re.compile(
    r"\s*(?:➖{2,}|➕{2,}|[-—|]{3,}|DM\s*[➡→>:📲]|\bDM\b\s*@).*$",
    re.IGNORECASE | re.DOTALL,
)


def _strip_noise(caption: str) -> str:
    """Strip channel watermark suffix, trailing emoji watermarks."""
    cleaned = _NOISE_RE.sub("", caption).strip()
    cleaned = re.sub(r"[^\w\s.''\-]+$", "", cleaned).strip()
    return cleaned

MAX_CONCURRENT = 8   # parallel Haiku vision calls


# ─── HTML parser ──────────────────────────────────────────────────────────────

class _MsgParser(HTMLParser):
    """Pull structured messages out of Telegram's exported HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: List[Dict[str, Any]] = []
        self._cur: Optional[Dict[str, Any]] = None
        self._in_from_name = False
        self._in_text = False
        self._in_strong = False
        self._last_from_name: str = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_d = dict(attrs)
        cls = attr_d.get("class", "") or ""

        if tag == "div" and "message default clearfix" in cls and "joined" not in cls:
            mid = attr_d.get("id", "")
            title = attr_d.get("title", "")
            self._cur = {
                "id": mid,
                "timestamp": None,
                "sender": self._last_from_name,
                "caption": "",
                "photos": [],
                "joined": False,
            }
            self.messages.append(self._cur)

        elif tag == "div" and "message default clearfix joined" in cls:
            mid = attr_d.get("id", "")
            self._cur = {
                "id": mid,
                "timestamp": None,
                "sender": self._last_from_name,
                "caption": "",
                "photos": [],
                "joined": True,
            }
            self.messages.append(self._cur)

        elif tag == "div" and "pull_right date details" in cls:
            ts_raw = attr_d.get("title", "")
            if self._cur and ts_raw:
                # "22.06.2026 08:09:21 UTC-08:00"
                try:
                    self._cur["timestamp"] = datetime.strptime(
                        ts_raw[:19], "%d.%m.%Y %H:%M:%S"
                    )
                except ValueError:
                    pass

        elif tag == "div" and cls.strip() == "from_name":
            self._in_from_name = True

        elif tag == "div" and cls.strip() == "text":
            self._in_text = True

        elif tag == "strong" and self._in_text:
            self._in_strong = True

        elif tag == "a" and "photo_wrap" in cls and self._cur is not None:
            href = attr_d.get("href", "")
            if href and "_thumb" not in href:
                self._cur["photos"].append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "div":
            self._in_from_name = False
            self._in_text = False
        if tag == "strong":
            self._in_strong = False

    def handle_data(self, data: str) -> None:
        if self._in_from_name:
            self._last_from_name = data.strip()
            if self._cur:
                self._cur["sender"] = self._last_from_name
        if self._in_text and self._cur is not None:
            self._cur["caption"] += data.strip()


def parse_html(export_dir: Path) -> List[Dict[str, Any]]:
    html_file = export_dir / "messages.html"
    if not html_file.exists():
        raise FileNotFoundError(f"messages.html not found in {export_dir}")
    parser = _MsgParser()
    parser.feed(html_file.read_text(encoding="utf-8", errors="replace"))
    return parser.messages


# ─── Message classification ───────────────────────────────────────────────────

def classify_message(msg: Dict[str, Any]) -> str:
    """Return 'recap', 'live', or 'promo'."""
    cap = msg.get("caption", "").strip()
    if not msg.get("photos"):
        return "promo"
    if not cap:
        # No caption at all — treat as a live pick (bare image from a capper)
        return "live"

    # 1. Result emoji present → recap (check BEFORE noise stripping)
    if RESULT_RE.search(cap):
        return "recap"

    # 2. Strip channel watermark noise to get the real name/caption
    cleaned = _strip_noise(cap)

    # 3. If nothing meaningful remains after stripping → promo
    if not cleaned:
        return "promo"

    # 4. Known promo text patterns (on cleaned text — watermark already removed)
    if PROMO_PATTERNS.search(cleaned):
        return "promo"

    # 5. Bullet-only / structural markers
    if cleaned in ("⏺", "•", "▪️", "◉"):
        return "promo"

    # 6. Looks promotional even after cleaning
    if _PROMO_FALLBACK.match(cleaned):
        return "promo"

    # Anything remaining is a capper attribution
    return "live"


# ─── Recap decoding ───────────────────────────────────────────────────────────

def decode_recap(caption: str) -> Tuple[Optional[str], int, int, int]:
    """
    Returns (capper_name, wins, losses, pushes).
    Example: "JS - ✅" → ("JS", 1, 0, 0)
             "ISW - ✅❌✅" → ("ISW", 2, 1, 0)
    """
    cap = caption.strip()
    m = RECAP_RE.match(cap)
    if m:
        capper = m.group(1).strip().rstrip("-–—").strip()
        emoji_str = m.group(2)
    else:
        capper = None
        emoji_str = cap

    wins = emoji_str.count(WIN_EMOJI)
    losses = emoji_str.count(LOSS_EMOJI)
    pushes = emoji_str.count(PUSH_EMOJI)
    return (capper or None, wins, losses, pushes)


# ─── Vision extraction ────────────────────────────────────────────────────────

async def extract_picks_for_message(
    msg: Dict[str, Any], export_dir: Path
) -> List[Dict[str, Any]]:
    """Run vision extraction on all photos in a message; merge picks."""
    caption = msg.get("caption", "")
    # Capper name from caption — strip watermark noise, then clean.
    # Trust caption over vision since the HTML gives us sender context.
    _cap_stripped = _strip_noise(re.sub(r"[✅❌⬛✓☑\s]*$", "", caption).strip())
    capper_from_caption = parse_router.clean_capper_name(_cap_stripped) if _cap_stripped else None

    all_picks: List[Dict[str, Any]] = []
    for photo_rel in msg.get("photos", []):
        photo_path = export_dir / photo_rel
        if not photo_path.exists():
            logger.warning("Photo not found: %s", photo_path)
            continue
        image_bytes = photo_path.read_bytes()
        result = await parse_router.extract_picks(image_bytes)
        for pick in result.get("picks", []):
            pick["_capper"] = capper_from_caption or result.get("capper_name")
            pick["_engine"] = result.get("engine")
            pick["_source_photo"] = photo_rel
            pick["_message_id"] = msg.get("id")
            pick["_timestamp"] = msg.get("timestamp").isoformat() if msg.get("timestamp") else None
            all_picks.append(pick)

    return all_picks


async def extract_all_live_picks(
    live_msgs: List[Dict[str, Any]], export_dir: Path
) -> List[Dict[str, Any]]:
    """Extract picks from all live messages with bounded concurrency."""
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def bounded(msg: Dict[str, Any]) -> List[Dict[str, Any]]:
        async with sem:
            try:
                return await extract_picks_for_message(msg, export_dir)
            except Exception as e:
                logger.error("Extraction failed for msg %s: %s", msg.get("id"), e)
                return []

    results = await asyncio.gather(*[bounded(m) for m in live_msgs])
    flat: List[Dict[str, Any]] = []
    for batch in results:
        flat.extend(batch)
    return flat


# ─── Game resolution ──────────────────────────────────────────────────────────

_scoreboard_cache: Dict[Tuple[str, str], List] = {}


async def resolve_game_key(pick: Dict[str, Any], game_date: datetime) -> Optional[str]:
    """
    Return a canonical "Away @ Home" game key for a pick.
    Uses match_key from vision if available, else fetches ESPN scoreboard.
    """
    # Use vision-provided match_key if we have one
    mk = pick.get("match_key")
    if mk:
        return mk.replace(" vs ", " @ ").replace(" v. ", " @ ")

    pick_text = pick.get("pick_text", "")
    pick_type = detect_pick_type(pick_text)

    # Totals and props without a named team pair can't be resolved to a side
    if pick_type in ("prop",):
        return None

    team_token = extract_team_from_pick_text(pick_text)
    if not team_token:
        return None

    # Get canonical full name + league
    full_name = get_full_team_name(team_token) or team_token
    league = pick.get("league")
    if not league:
        league, _ = detect_league_from_team(team_token)
    if not league:
        return None

    lu = league.upper()
    cache_key = (lu, game_date.strftime("%Y%m%d"))
    if cache_key not in _scoreboard_cache:
        games = await fetch_scoreboard(lu, game_date)
        _scoreboard_cache[cache_key] = games
    games = _scoreboard_cache[cache_key]

    game = find_matching_game(games, full_name)
    if not game:
        return None

    return f"{game.away_team} @ {game.home_team}"


# ─── Side normalisation ───────────────────────────────────────────────────────

def extract_side(pick: Dict[str, Any]) -> Optional[str]:
    """
    Return a normalised side token:
      spread/ML  → canonical team name (or first word)
      over       → "OVER <line>"
      under      → "UNDER <line>"
      prop       → None (unresolvable for consensus)
    """
    pick_text = pick.get("pick_text", "")
    pick_type = detect_pick_type(pick_text)

    if pick_type == "prop":
        return None
    if pick_type in ("over", "under"):
        line = _extract_ou_line(pick_text)
        if line is not None:
            return f"{pick_type.upper()} {line}"
        return pick_type.upper()
    # spread or moneyline → team
    team_token = extract_team_from_pick_text(pick_text)
    if not team_token:
        return None
    full = get_full_team_name(team_token)
    return full or team_token


# ─── Convergence scoring ─────────────────────────────────────────────────────

def compute_convergence(resolved_picks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Returns {
      "consensus": [...],   sorted list of games with high agreement
      "conflicts": [...],   games where cappers are split
      "unmatched": [...],   picks that couldn't be resolved to a game
    }
    """
    # Group by (game_key, market) → {side → set of cappers}
    groups: Dict[Tuple[str, str], Dict[str, set]] = {}
    unmatched: List[Dict[str, Any]] = []

    for p in resolved_picks:
        gk = p.get("_game_key")
        side = p.get("_side")
        if not gk or not side:
            unmatched.append(p)
            continue
        market = detect_pick_type(p.get("pick_text", ""))
        key = (gk, market)
        if key not in groups:
            groups[key] = {}
        capper = p.get("_capper") or "unknown"
        groups[key].setdefault(side, set()).add(capper)

    consensus = []
    conflicts = []

    for (game_key, market), sides in groups.items():
        # Total unique cappers across all sides
        all_cappers: set = set()
        for s in sides.values():
            all_cappers |= s
        total_cappers = len(all_cappers)

        if total_cappers < 2:
            continue  # Skip single-capper picks for convergence

        # Sort sides by capper count
        sorted_sides = sorted(sides.items(), key=lambda x: len(x[1]), reverse=True)
        dominant_side, dominant_cappers = sorted_sides[0]
        dominant_count = len(dominant_cappers)
        share = dominant_count / total_cappers

        entry = {
            "game": game_key,
            "market": market,
            "total_cappers": total_cappers,
            "sides": {side: sorted(cappers) for side, cappers in sorted_sides},
            "dominant_side": dominant_side,
            "dominant_count": dominant_count,
            "share_pct": round(share * 100, 1),
        }

        # Conflict: 2nd side has ≥ 2 cappers (meaningful opposition)
        is_conflict = len(sorted_sides) > 1 and len(sorted_sides[1][1]) >= 2

        if is_conflict:
            entry["conflict_side"] = sorted_sides[1][0]
            entry["conflict_count"] = len(sorted_sides[1][1])
            conflicts.append(entry)
        elif dominant_count >= 3:
            consensus.append(entry)
        # else: 2-capper agreement, put in consensus anyway at low confidence
        elif dominant_count == 2:
            entry["note"] = "only 2 cappers — low confidence"
            consensus.append(entry)

    consensus.sort(key=lambda x: (-x["dominant_count"], -x["share_pct"]))
    conflicts.sort(key=lambda x: -x["total_cappers"])

    return {"consensus": consensus, "conflicts": conflicts, "unmatched": unmatched}


# ─── Output formatters ────────────────────────────────────────────────────────

def write_results_csv(recap_rows: List[Dict[str, Any]], out_path: Path) -> None:
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["capper", "won", "lost", "pushed", "record", "raw_emoji", "timestamp"]
        )
        writer.writeheader()
        for row in sorted(recap_rows, key=lambda r: r["capper"] or ""):
            writer.writerow(row)
    print(f"  ✍️  Results CSV → {out_path}")


def write_convergence_report(
    result: Dict[str, Any],
    out_path: Path,
    date_str: str,
    total_live: int,
    total_picks: int,
) -> None:
    lines = [
        f"# Convergence / Conflict Report — {date_str}",
        "",
        f"**Live messages processed**: {total_live}  ",
        f"**Total picks extracted**: {total_picks}  ",
        "",
        "---",
        "",
    ]

    consensus = result["consensus"]
    conflicts = result["conflicts"]
    unmatched = result["unmatched"]

    lines.append(f"## 🟢 Consensus plays ({len(consensus)} games)\n")
    lines.append(
        "_Same side, ≥2 distinct cappers. High share = stronger agreement._\n"
    )
    if consensus:
        lines.append("| Game | Market | Side | Cappers | Share | Who |")
        lines.append("|---|---|---|---|---|---|")
        for e in consensus:
            note = f" ⚠️ {e.get('note', '')}" if e.get("note") else ""
            cappers_str = ", ".join(e["sides"].get(e["dominant_side"], []))
            lines.append(
                f"| {e['game']} | {e['market']} | **{e['dominant_side']}** "
                f"| {e['dominant_count']} | {e['share_pct']}% | {cappers_str}{note} |"
            )
    else:
        lines.append("_No games with ≥2 cappers on the same side._")

    lines += ["", "---", "", f"## 🔴 Conflict games ({len(conflicts)} games)\n"]
    lines.append(
        "_Both sides have meaningful support — the market is split. "
        "Analyze before acting; or pass._\n"
    )
    if conflicts:
        lines.append("| Game | Market | Side A | Count | Side B | Count |")
        lines.append("|---|---|---|---|---|---|")
        for e in conflicts:
            sa, sc = e["dominant_side"], e["dominant_count"]
            sb, sbc = e["conflict_side"], e["conflict_count"]
            lines.append(f"| {e['game']} | {e['market']} | {sa} | {sc} | {sb} | {sbc} |")
    else:
        lines.append("_No games with meaningful capper disagreement._")

    lines += [
        "",
        "---",
        "",
        f"## ⚪ Unmatched picks ({len(unmatched)} picks)\n",
        "_Props, totals without a game context, or picks that couldn't be "
        "resolved to a game. Not included in convergence._\n",
    ]
    if unmatched:
        lines.append("| Pick | Capper | Sport |")
        lines.append("|---|---|---|")
        for p in unmatched[:30]:
            lines.append(
                f"| {p.get('pick_text', '?')} | {p.get('_capper', '?')} "
                f"| {p.get('sport', '?')} |"
            )
        if len(unmatched) > 30:
            lines.append(f"| _… and {len(unmatched) - 30} more_ | | |")

    lines += [
        "",
        "---",
        "",
        "## ⚠️ Premise caveat",
        "",
        "These are **free Telegram repost accounts**, not independent Vegas sharps. "
        "Free-channel consensus likely tracks *public money* (often the fade side). "
        "Cappers may tail each other, making agreement non-independent. "
        "**Validate with a backtest before acting on convergence signal.**",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  📊 Convergence report → {out_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main(export_dir_str: str) -> None:
    export_dir = Path(export_dir_str).expanduser().resolve()
    if not export_dir.is_dir():
        print(f"Error: {export_dir} is not a directory")
        sys.exit(1)

    # Infer date from folder name or today
    folder_name = export_dir.name
    m = re.search(r"(\d{4}-\d{2}-\d{2})", folder_name)
    if m:
        date_str = m.group(1)
        game_date = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        game_date = datetime.utcnow()
        date_str = game_date.strftime("%Y-%m-%d")

    date_compact = date_str.replace("-", "")

    # Check ANTHROPIC_API_KEY — vision mode silently returns empty without it
    from app.config import settings as _cfg
    if not _cfg.ANTHROPIC_API_KEY:
        print("\n❌ ANTHROPIC_API_KEY is not set in backend/.env")
        print("   Add it to backend/.env:")
        print("   ANTHROPIC_API_KEY=sk-ant-...")
        print("   Get one at: https://console.anthropic.com/settings/keys\n")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  CAPFREE Convergence Report — {date_str}")
    print(f"  Export: {export_dir}")
    print(f"  Model: {_cfg.VISION_MODEL}")
    print(f"{'='*60}\n")

    # 1. Parse HTML
    print("⏳ Parsing messages.html …")
    messages = parse_html(export_dir)
    print(f"   {len(messages)} messages found")

    # 2. Classify
    recap_msgs, live_msgs, promo_msgs = [], [], []
    for msg in messages:
        kind = classify_message(msg)
        if kind == "recap":
            recap_msgs.append(msg)
        elif kind == "live":
            live_msgs.append(msg)
        else:
            promo_msgs.append(msg)

    print(f"   Recap: {len(recap_msgs)}  Live: {len(live_msgs)}  Promo/skip: {len(promo_msgs)}")

    # 3. Results harvest from recap captions
    print("\n⏳ Decoding result recap captions …")
    recap_rows = []
    for msg in recap_msgs:
        cap = msg.get("caption", "").strip()
        capper, wins, losses, pushes = decode_recap(cap)
        total = wins + losses + pushes
        row = {
            "capper": capper or cap[:40],
            "won": wins,
            "lost": losses,
            "pushed": pushes,
            "record": f"{wins}-{losses}" + (f"-{pushes}" if pushes else ""),
            "raw_emoji": "".join(c for c in cap if c in (WIN_EMOJI, LOSS_EMOJI, PUSH_EMOJI)),
            "timestamp": msg.get("timestamp").isoformat() if msg.get("timestamp") else "",
        }
        recap_rows.append(row)
        print(f"   {row['capper']:30s} {row['record']}")

    results_path = export_dir / f"results_{date_compact}.csv"
    write_results_csv(recap_rows, results_path)

    # 4. Live pick extraction
    print(f"\n⏳ Extracting picks from {len(live_msgs)} live messages via Claude vision …")
    print("   (this may take 1–3 minutes)\n")
    raw_picks = await extract_all_live_picks(live_msgs, export_dir)
    print(f"\n   Extracted {len(raw_picks)} picks from live messages")

    # Save raw picks for debug
    raw_path = export_dir / f"picks_raw_{date_compact}.json"
    raw_path.write_text(
        json.dumps(raw_picks, indent=2, default=str), encoding="utf-8"
    )
    print(f"  💾 Raw picks → {raw_path}")

    # 5. Resolve game keys
    print("\n⏳ Resolving game keys via ESPN scoreboard …")
    for pick in raw_picks:
        try:
            gk = await resolve_game_key(pick, game_date)
        except Exception as e:
            logger.debug("Game resolution failed: %s", e)
            gk = None
        pick["_game_key"] = gk
        pick["_side"] = extract_side(pick) if gk else None

    resolved = sum(1 for p in raw_picks if p.get("_game_key"))
    print(f"   {resolved}/{len(raw_picks)} picks resolved to a game")

    # 6. Convergence / conflict
    print("\n⏳ Computing convergence / conflict …")
    result = compute_convergence(raw_picks)
    print(
        f"   Consensus: {len(result['consensus'])} games  "
        f"Conflicts: {len(result['conflicts'])} games  "
        f"Unmatched: {len(result['unmatched'])} picks"
    )

    # 7. Write report
    conv_path = export_dir / f"convergence_{date_compact}.md"
    write_convergence_report(
        result, conv_path, date_str, len(live_msgs), len(raw_picks)
    )

    # 8. Summary to console
    print(f"\n{'='*60}")
    print("  TOP CONSENSUS PLAYS")
    print(f"{'='*60}")
    for e in result["consensus"][:10]:
        cappers = ", ".join(e["sides"].get(e["dominant_side"], []))
        print(
            f"  {e['game'][:40]:<42} {e['market']:<10} "
            f"▶ {e['dominant_side']} ({e['dominant_count']} cappers, {e['share_pct']}%)"
        )
        print(f"    Who: {cappers}")

    if result["conflicts"]:
        print(f"\n{'='*60}")
        print("  CONFLICT GAMES (split — both sides have support)")
        print(f"{'='*60}")
        for e in result["conflicts"][:10]:
            print(
                f"  {e['game'][:40]:<42} {e['market']:<10} "
                f"  {e['dominant_side']} ({e['dominant_count']}) vs "
                f"{e['conflict_side']} ({e['conflict_count']})"
            )

    print(f"\n✅ Done. Outputs written to: {export_dir}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
