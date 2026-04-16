from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timedelta
import logging
from .. import models, schemas, database
from ..services.espn_service import grade_pick_with_espn, detect_pick_type, UNSUPPORTED_LEAGUES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/picks",
    tags=["picks"],
)


def _calculate_profit(result: str, odds: Optional[int], units_risked: float) -> float:
    if result == "WIN":
        if odds:
            if odds > 0:
                profit = (odds / 100) * units_risked
            else:
                profit = (100 / abs(odds)) * units_risked
        else:
            profit = units_risked
        return round(profit, 2)
    elif result == "LOSS":
        return -units_risked
    else:  # PUSH or PENDING
        return 0.0


async def _find_duplicate_pick(
    db: AsyncSession,
    capper_id: int,
    pick_text: str,
    game_date: Optional[datetime],
) -> Optional[models.Pick]:
    """
    Return an existing pick if one with the same capper + pick_text already
    exists within a 7-day window (using game_date when available).
    """
    norm_text = pick_text.strip().lower()
    cutoff = datetime.utcnow() - timedelta(days=7)

    result = await db.execute(
        select(models.Pick)
        .options(selectinload(models.Pick.capper))
        .where(
            models.Pick.capper_id == capper_id,
            models.Pick.date >= cutoff,
        )
    )
    candidates = result.scalars().all()

    for p in candidates:
        if p.pick_text.strip().lower() != norm_text:
            continue
        # Match on game_date calendar day, or just text+capper if neither has a game_date
        p_day = (p.game_date or p.date).date()
        new_day = (game_date or datetime.utcnow()).date()
        if p_day == new_day:
            return p

    return None


@router.post("/", response_model=schemas.Pick)
async def create_pick(
    pick: schemas.PickCreate,
    response: Response,
    db: AsyncSession = Depends(database.get_db),
):
    # Resolve or create capper
    result = await db.execute(select(models.Capper).where(models.Capper.name == pick.capper_name))
    capper = result.scalars().first()

    if not capper:
        capper = models.Capper(name=pick.capper_name)
        db.add(capper)
        await db.commit()
        await db.refresh(capper)

    # Duplicate check — return existing pick rather than inserting a copy
    existing = await _find_duplicate_pick(db, capper.id, pick.pick_text, pick.game_date)
    if existing:
        logger.info(f"Duplicate pick skipped: '{pick.pick_text}' for capper {capper.name}")
        response.headers["X-Duplicate"] = "true"
        return existing

    db_pick = models.Pick(
        capper_id=capper.id,
        sport=pick.sport,
        league=pick.league,
        match_key=pick.match_key,
        pick_text=pick.pick_text,
        units_risked=pick.units_risked,
        odds=pick.odds,
        result=pick.result,
        profit=pick.profit,
        original_image_path=pick.original_image_path,
        raw_text=pick.raw_text,
        game_date=pick.game_date,
    )
    db.add(db_pick)
    await db.commit()
    await db.refresh(db_pick)

    db_pick.capper = capper
    return db_pick


@router.get("/", response_model=List[schemas.Pick])
async def read_picks(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(
        select(models.Pick)
        .options(selectinload(models.Pick.capper))
        .offset(skip)
        .limit(limit)
        .order_by(models.Pick.date.desc())
    )
    picks = result.scalars().all()
    return picks


@router.post("/auto-grade", response_model=schemas.AutoGradeResult)
async def auto_grade_pending(db: AsyncSession = Depends(database.get_db)):
    """Auto-grade all PENDING picks using ESPN API."""
    result = await db.execute(
        select(models.Pick)
        .options(selectinload(models.Pick.capper))
        .where(models.Pick.result == "PENDING")
    )
    pending_picks = result.scalars().all()

    total_pending = len(pending_picks)
    graded_by_api = 0
    auto_win_count = 0
    skipped_not_final = 0
    errors: list[str] = []

    games_cache: dict = {}
    now = datetime.utcnow()

    for pick in pending_picks:
        try:
            league = (pick.league or pick.sport or "").upper()
            pick_type = detect_pick_type(pick.pick_text)
            sport_str = pick.sport or ""
            is_unsupported = any(u.lower() in sport_str.lower() for u in UNSUPPORTED_LEAGUES)
            is_prop = pick_type == "prop"

            # Use game_date for ESPN lookups if set; fall back to upload date
            lookup_date = pick.game_date or pick.date

            # Try ESPN grading first
            grade_result = None
            if not is_unsupported and league:
                grade_result = await grade_pick_with_espn(
                    pick.pick_text,
                    league,
                    lookup_date,
                    games_cache,
                )

            if grade_result is not None:
                # ESPN found and graded it
                pick.result = grade_result
                pick.profit = _calculate_profit(grade_result, pick.odds, pick.units_risked)
                pick.grade_source = "espn_api"
                pick.graded_at = now
                graded_by_api += 1
            elif is_unsupported or is_prop:
                # Prop or unsupported league — auto-win
                pick.result = "WIN"
                pick.profit = _calculate_profit("WIN", pick.odds, pick.units_risked)
                pick.grade_source = "auto_win"
                pick.graded_at = now
                auto_win_count += 1
            else:
                # Game not found in ESPN — auto-win only if game_date (or upload date) is >24h ago
                age_hours = (now - (pick.game_date or pick.date)).total_seconds() / 3600
                if age_hours > 24:
                    pick.result = "WIN"
                    pick.profit = _calculate_profit("WIN", pick.odds, pick.units_risked)
                    pick.grade_source = "auto_win"
                    pick.graded_at = now
                    auto_win_count += 1
                else:
                    skipped_not_final += 1

        except Exception as e:
            errors.append(f"Pick {pick.id}: {str(e)}")
            skipped_not_final += 1

    await db.commit()

    return schemas.AutoGradeResult(
        total_pending=total_pending,
        graded_by_api=graded_by_api,
        auto_win=auto_win_count,
        skipped_not_final=skipped_not_final,
        errors=errors,
    )


@router.post("/bulk-grade", response_model=schemas.BulkGradeResult)
async def bulk_grade_picks(payload: schemas.BulkGradeRequest, db: AsyncSession = Depends(database.get_db)):
    """Grade multiple picks at once with the same result."""
    result = await db.execute(
        select(models.Pick)
        .where(models.Pick.id.in_(payload.pick_ids))
    )
    picks = result.scalars().all()

    graded = 0
    skipped = 0
    now = datetime.utcnow()
    for pick in picks:
        if pick.result != "PENDING":
            skipped += 1
            continue
        pick.result = payload.result.value
        pick.profit = _calculate_profit(payload.result.value, pick.odds, pick.units_risked)
        pick.grade_source = "manual"
        pick.graded_at = now
        graded += 1

    await db.commit()
    return schemas.BulkGradeResult(graded=graded, skipped=skipped)


@router.get("/{pick_id}", response_model=schemas.Pick)
async def read_pick(pick_id: int, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(
        select(models.Pick)
        .options(selectinload(models.Pick.capper))
        .where(models.Pick.id == pick_id)
    )
    pick = result.scalars().first()
    if pick is None:
        raise HTTPException(status_code=404, detail="Pick not found")
    return pick


@router.patch("/{pick_id}", response_model=schemas.Pick)
async def update_pick(pick_id: int, pick_update: schemas.PickUpdate, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Pick).where(models.Pick.id == pick_id))
    db_pick = result.scalars().first()
    if db_pick is None:
        raise HTTPException(status_code=404, detail="Pick not found")

    update_data = pick_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_pick, key, value)

    await db.commit()
    await db.refresh(db_pick)
    return db_pick


@router.get("/by-capper/{capper_id}", response_model=List[schemas.Pick])
async def get_picks_by_capper(capper_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(database.get_db)):
    """Get all picks for a specific capper"""
    # Verify capper exists
    result = await db.execute(select(models.Capper).where(models.Capper.id == capper_id))
    capper = result.scalars().first()
    if capper is None:
        raise HTTPException(status_code=404, detail="Capper not found")

    result = await db.execute(
        select(models.Pick)
        .options(selectinload(models.Pick.capper))
        .where(models.Pick.capper_id == capper_id)
        .order_by(models.Pick.date.desc())
        .offset(skip)
        .limit(limit)
    )
    picks = result.scalars().all()
    return picks


@router.patch("/{pick_id}/grade", response_model=schemas.Pick)
async def grade_pick(pick_id: int, grade: schemas.PickGradeUpdate, db: AsyncSession = Depends(database.get_db)):
    """Grade a pick and calculate profit based on result and odds"""
    result = await db.execute(
        select(models.Pick)
        .options(selectinload(models.Pick.capper))
        .where(models.Pick.id == pick_id)
    )
    db_pick = result.scalars().first()
    if db_pick is None:
        raise HTTPException(status_code=404, detail="Pick not found")

    db_pick.result = grade.result.value
    db_pick.profit = _calculate_profit(grade.result.value, db_pick.odds, db_pick.units_risked)
    db_pick.grade_source = "manual"
    db_pick.graded_at = datetime.utcnow()

    await db.commit()
    await db.refresh(db_pick)
    return db_pick


@router.delete("/{pick_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pick(pick_id: int, db: AsyncSession = Depends(database.get_db)):
    """Delete a pick"""
    result = await db.execute(select(models.Pick).where(models.Pick.id == pick_id))
    db_pick = result.scalars().first()
    if db_pick is None:
        raise HTTPException(status_code=404, detail="Pick not found")

    await db.delete(db_pick)
    await db.commit()
    return None
