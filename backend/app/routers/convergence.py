"""
Convergence API — two endpoints:
  GET  /convergence/daily   — analyze picks already in DB for a given date
  POST /convergence/upload  — analyze a Telegram HTML export ZIP
"""
import asyncio
import logging
import re
import tempfile
import zipfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .. import models, database
from ..ocr import parse_router
from ..services.convergence import extract_side, resolve_game_key, compute_convergence

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/convergence", tags=["convergence"])

_MAX_ZIP_BYTES = 300 * 1024 * 1024   # 300 MB
_MAX_VISION_CONCURRENT = 6


# ─── Telegram HTML parser (mirrors convergence_report.py) ────────────────────

WIN_EMOJI = "✅"
LOSS_EMOJI = "❌"
PUSH_EMOJI = "⬛"
_RESULT_RE = re.compile(r"[✅❌⬛]")
_RECAP_RE = re.compile(r"^(.+?)(?:\s*[-–—]\s*)?([✅❌⬛]+)\s*$")
_PROMO_RE = re.compile(
    r"cheapest|prices in the industry|join the best|guarantee:|bonus capper|"
    r"for any question|reach out|everyone'?s favorite|pay per view|ppv|"
    r"subscribe|follow us|sign up|\bfree\b.*trial|\bbankroll\b(?!\w)",
    re.IGNORECASE,
)
_NOISE_RE = re.compile(
    r"\s*(?:➖{2,}|➕{2,}|[-—|]{3,}|DM\s*[➡→>:📲]|\bDM\b\s*@).*$",
    re.IGNORECASE | re.DOTALL,
)


def _strip_noise(caption: str) -> str:
    cleaned = _NOISE_RE.sub("", caption).strip()
    return re.sub(r"[^\w\s.''\-]+$", "", cleaned).strip()


class _MsgParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.messages: List[Dict[str, Any]] = []
        self._cur: Optional[Dict[str, Any]] = None
        self._in_from_name = False
        self._in_text = False
        self._last_from_name = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        d = dict(attrs)
        cls = d.get("class", "") or ""

        if tag == "div" and "message default clearfix" in cls:
            joined = "joined" in cls
            self._cur = {
                "id": d.get("id", ""),
                "timestamp": None,
                "sender": self._last_from_name,
                "caption": "",
                "photos": [],
                "joined": joined,
            }
            self.messages.append(self._cur)

        elif tag == "div" and "pull_right date details" in cls:
            ts_raw = d.get("title", "")
            if self._cur and ts_raw:
                try:
                    self._cur["timestamp"] = datetime.strptime(ts_raw[:19], "%d.%m.%Y %H:%M:%S")
                except ValueError:
                    pass

        elif tag == "div" and cls.strip() == "from_name":
            self._in_from_name = True

        elif tag == "div" and cls.strip() == "text":
            self._in_text = True

        elif tag == "a" and "photo_wrap" in cls and self._cur is not None:
            href = d.get("href", "")
            if href and "_thumb" not in href:
                self._cur["photos"].append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "div":
            self._in_from_name = False
            self._in_text = False

    def handle_data(self, data: str) -> None:
        if self._in_from_name:
            self._last_from_name = data.strip()
            if self._cur:
                self._cur["sender"] = self._last_from_name
        if self._in_text and self._cur is not None:
            self._cur["caption"] += data.strip()


def _classify(msg: Dict[str, Any]) -> str:
    cap = msg.get("caption", "").strip()
    if not msg.get("photos"):
        return "promo"
    if not cap:
        return "live"
    if _RESULT_RE.search(cap):
        return "recap"
    cleaned = _strip_noise(cap)
    if not cleaned or _PROMO_RE.search(cleaned):
        return "promo"
    if cleaned in ("⏺", "•", "▪️", "◉"):
        return "promo"
    return "live"


def _decode_recap(caption: str) -> Tuple[Optional[str], int, int, int]:
    m = _RECAP_RE.match(caption.strip())
    if m:
        capper = m.group(1).strip().rstrip("-–—").strip()
        emojis = m.group(2)
    else:
        capper = None
        emojis = caption
    return (
        capper or None,
        emojis.count(WIN_EMOJI),
        emojis.count(LOSS_EMOJI),
        emojis.count(PUSH_EMOJI),
    )


async def _extract_picks_from_msg(
    msg: Dict[str, Any], export_dir: Path
) -> List[Dict[str, Any]]:
    cap = msg.get("caption", "")
    cleaned = _strip_noise(re.sub(r"[✅❌⬛✓☑\s]*$", "", cap).strip())
    capper_from_cap = parse_router.clean_capper_name(cleaned) if cleaned else None

    picks: List[Dict[str, Any]] = []
    for photo_rel in msg.get("photos", []):
        photo_path = export_dir / photo_rel
        if not photo_path.exists():
            continue
        result = await parse_router.extract_picks(photo_path.read_bytes())
        for pick in result.get("picks", []):
            pick["_capper"] = capper_from_cap or result.get("capper_name")
            pick["_message_id"] = msg.get("id")
            pick["_timestamp"] = msg["timestamp"].isoformat() if msg.get("timestamp") else None
            picks.append(pick)
    return picks


async def _extract_all(
    live_msgs: List[Dict[str, Any]], export_dir: Path
) -> List[Dict[str, Any]]:
    sem = asyncio.Semaphore(_MAX_VISION_CONCURRENT)

    async def bounded(msg: Dict[str, Any]) -> List[Dict[str, Any]]:
        async with sem:
            try:
                return await _extract_picks_from_msg(msg, export_dir)
            except Exception as e:
                logger.error("Vision extraction failed for msg %s: %s", msg.get("id"), e)
                return []

    batches = await asyncio.gather(*[bounded(m) for m in live_msgs])
    return [p for batch in batches for p in batch]


# ─── Option A: DB-based daily convergence ────────────────────────────────────

@router.get("/daily")
async def daily_convergence(
    date: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to today"),
    db: AsyncSession = Depends(database.get_db),
):
    if date:
        try:
            target_dt = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    else:
        target_dt = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    date_str = target_dt.strftime("%Y-%m-%d")

    result = await db.execute(
        select(models.Pick, models.Capper)
        .join(models.Capper, models.Pick.capper_id == models.Capper.id)
        .where(func.date(models.Pick.game_date) == target_dt.date())
    )
    rows = result.all()

    picks: List[Dict[str, Any]] = []
    for pick, capper in rows:
        d: Dict[str, Any] = {
            "pick_text": pick.pick_text or "",
            "match_key": pick.match_key,
            "league": pick.league,
            "sport": pick.sport,
            "_capper": capper.name,
        }
        d["_side"] = extract_side(d)
        if pick.match_key:
            d["_game_key"] = pick.match_key.replace(" vs ", " @ ").replace(" v. ", " @ ")
        elif pick.game_date:
            try:
                d["_game_key"] = await resolve_game_key(d, pick.game_date)
            except Exception:
                d["_game_key"] = None
        else:
            d["_game_key"] = None
        picks.append(d)

    conv = compute_convergence(picks)
    return {
        "date": date_str,
        "source": "db",
        "total_picks": len(picks),
        "consensus": conv["consensus"],
        "conflicts": conv["conflicts"],
        "unmatched_count": len(conv["unmatched"]),
    }


# ─── Option B: Telegram export ZIP upload ────────────────────────────────────

@router.post("/upload")
async def upload_convergence(
    file: UploadFile = File(...),
    date: Optional[str] = Query(None, description="YYYY-MM-DD override; inferred from messages if omitted"),
):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload must be a .zip file")

    raw = await file.read()
    if len(raw) > _MAX_ZIP_BYTES:
        raise HTTPException(status_code=413, detail="ZIP too large (max 300 MB)")

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            with zipfile.ZipFile(__import__("io").BytesIO(raw)) as zf:
                zf.extractall(tmpdir)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Could not read ZIP file")

        export_dir = Path(tmpdir)
        # Try common Telegram export layouts: flat or one sub-folder
        html_candidates = list(export_dir.glob("messages.html")) + list(export_dir.glob("*/messages.html"))
        if not html_candidates:
            raise HTTPException(status_code=422, detail="No messages.html found in ZIP")
        html_path = html_candidates[0]
        export_dir = html_path.parent

        # Parse
        parser = _MsgParser()
        parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
        messages = parser.messages

        # Infer game date
        if date:
            try:
                game_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
        else:
            timestamps = [m["timestamp"] for m in messages if m.get("timestamp")]
            game_date = min(timestamps) if timestamps else datetime.utcnow()

        date_str = game_date.strftime("%Y-%m-%d")

        # Classify
        recap_msgs = [m for m in messages if _classify(m) == "recap"]
        live_msgs = [m for m in messages if _classify(m) == "live"]

        # Recap results
        recap_results = []
        for msg in recap_msgs:
            cap = msg.get("caption", "").strip()
            capper, wins, losses, pushes = _decode_recap(cap)
            recap_results.append({
                "capper": capper or cap[:40],
                "won": wins,
                "lost": losses,
                "pushed": pushes,
                "record": f"{wins}-{losses}" + (f"-{pushes}" if pushes else ""),
            })

        # Vision extraction
        raw_picks = await _extract_all(live_msgs, export_dir)

        # Resolve game keys
        for pick in raw_picks:
            try:
                pick["_game_key"] = await resolve_game_key(pick, game_date)
            except Exception:
                pick["_game_key"] = None
            pick["_side"] = extract_side(pick) if pick.get("_game_key") else None

        conv = compute_convergence(raw_picks)

        return {
            "date": date_str,
            "source": "telegram_export",
            "total_picks": len(raw_picks),
            "live_messages": len(live_msgs),
            "recap_messages": len(recap_msgs),
            "consensus": conv["consensus"],
            "conflicts": conv["conflicts"],
            "unmatched_count": len(conv["unmatched"]),
            "recap_results": sorted(recap_results, key=lambda r: r["capper"] or ""),
        }
