"""
OCR-first parse with optional escalation to Claude vision.

Hybrid flow (default):
  1. Run Tesseract OCR + regex parser (free, fast).
  2. If result looks reliable → return it.
  3. If unreliable → call vision_parser (Claude Haiku).
  4. If vision also returns nothing → return the OCR result anyway.

PARSE_ENGINE config:
  "hybrid"  — OCR first, escalate when unreliable (default)
  "ocr"     — always use OCR only (today's behavior)
  "vision"  — always use vision (testing)
"""
import logging
from typing import Any, Dict, List

from ..config import settings
from . import parser, pipeline
from . import vision_parser

logger = logging.getLogger(__name__)


def _is_unreliable(raw_text: str, picks: List[Dict[str, Any]]) -> bool:
    """Return True when the OCR result is not trustworthy."""
    if not picks:
        return True
    if len(raw_text.strip()) < 100:
        return True
    # Garbage-heavy text: less than 55% alphanumeric+whitespace chars
    alnum = sum(1 for c in raw_text if c.isalnum() or c.isspace())
    if len(raw_text) > 0 and alnum / len(raw_text) < 0.55:
        return True
    # All picks are missing every useful field (units defaulted, no odds, unknown sport)
    def _low_confidence(p: Dict[str, Any]) -> bool:
        return (
            p.get("units_risked", 1.0) == 1.0
            and p.get("odds") is None
            and (p.get("sport") or "Unknown") == "Unknown"
        )
    if all(_low_confidence(p) for p in picks):
        return True
    return False


async def extract_picks(image_bytes: bytes) -> Dict[str, Any]:
    """
    Route image through OCR and/or vision depending on PARSE_ENGINE setting.

    Returns:
        {
            "capper_name": str | None,
            "picks": list[dict],   # same shape as parser.parse_picks output
            "engine": "ocr" | "vision",
            "raw_text": str,       # OCR text (empty string if vision-only)
        }
    """
    engine = settings.PARSE_ENGINE

    raw_text = ""
    ocr_picks: List[Dict[str, Any]] = []
    ocr_capper = None

    if engine != "vision":
        raw_text = pipeline.extract_text(image_bytes)
        ocr_picks = parser.parse_picks(raw_text)
        ocr_capper = parser.extract_capper_name(raw_text)
        logger.debug(
            "OCR produced %d picks (engine=%s, text_len=%d)",
            len(ocr_picks),
            engine,
            len(raw_text),
        )

    use_vision = engine == "vision" or (
        engine == "hybrid" and _is_unreliable(raw_text, ocr_picks)
    )

    if use_vision:
        logger.info("Escalating to vision parser (engine=%s)", engine)
        vision_result = await vision_parser.parse_picks_from_image(image_bytes)
        if vision_result["picks"]:
            return {
                "capper_name": vision_result.get("capper_name") or ocr_capper,
                "picks": vision_result["picks"],
                "engine": "vision",
                "raw_text": raw_text,
            }
        # Vision was called but returned nothing — do NOT silently fall back to
        # unreliable OCR output. Signal failure so callers can surface it.
        logger.warning(
            "Vision returned no picks (ocr_picks=%d, raw_text_len=%d) — "
            "returning empty to avoid persisting bad data",
            len(ocr_picks),
            len(raw_text),
        )
        return {
            "capper_name": None,
            "picks": [],
            "engine": "vision_failed",
            "raw_text": raw_text,
        }

    return {
        "capper_name": ocr_capper,
        "picks": ocr_picks,
        "engine": "ocr",
        "raw_text": raw_text,
    }
