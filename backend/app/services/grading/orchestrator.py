from datetime import datetime
from typing import Optional, Tuple

from . import rules
from .pick_text import detect_pick_type
from .espn import EspnSource
from .sofascore import SofascoreSource

SOURCES = [EspnSource(), SofascoreSource()]


async def grade_pick(
    pick_text: str,
    league: str,
    pick_date: datetime,
    cache: dict,
) -> Optional[Tuple[str, Optional[datetime]]]:
    """
    Attempt to grade a single pick using registered data sources in priority order.
    Returns (result, match_date) where result is "WIN"|"LOSS"|"PUSH" and
    match_date is the fixture's date when known. Returns None if ungradeable.
    """
    league_upper = (league or "").upper()
    if not league_upper:
        return None

    pick_type = detect_pick_type(pick_text)

    for source in SOURCES:
        if not source.supports(league_upper):
            continue
        records = await source.fetch(league_upper, pick_date, cache)
        graded = rules.grade_records(records, pick_text, pick_type)
        if graded is not None:
            return graded

    return None
