from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from .. import models, schemas, database

router = APIRouter(
    prefix="/picks",
    tags=["picks"],
)

@router.post("/", response_model=schemas.Pick)
async def create_pick(pick: schemas.PickCreate, db: AsyncSession = Depends(database.get_db)):
    # Check if capper exists, if not create
    result = await db.execute(select(models.Capper).where(models.Capper.name == pick.capper_name))
    capper = result.scalars().first()
    
    if not capper:
        capper = models.Capper(name=pick.capper_name)
        db.add(capper)
        await db.commit()
        await db.refresh(capper)
    
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
        raw_text=pick.raw_text
    )
    db.add(db_pick)
    await db.commit()
    await db.refresh(db_pick)
    
    # Manually set the capper relationship to avoid lazy load error
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
    
    # Update result
    db_pick.result = grade.result.value
    
    # Calculate profit based on result
    if grade.result == schemas.PickResult.WIN:
        # Calculate profit based on American odds
        if db_pick.odds:
            if db_pick.odds > 0:
                # Positive odds: profit = (odds / 100) * units_risked
                profit = (db_pick.odds / 100) * db_pick.units_risked
            else:
                # Negative odds: profit = (100 / abs(odds)) * units_risked
                profit = (100 / abs(db_pick.odds)) * db_pick.units_risked
        else:
            # Default to even money if no odds specified
            profit = db_pick.units_risked
        db_pick.profit = round(profit, 2)
    elif grade.result == schemas.PickResult.LOSS:
        # Loss: negative units risked
        db_pick.profit = -db_pick.units_risked
    else:  # PUSH or PENDING
        # Push: no profit or loss
        db_pick.profit = 0.0
    
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

