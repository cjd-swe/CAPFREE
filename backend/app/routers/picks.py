from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
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
    return db_pick

@router.get("/", response_model=List[schemas.Pick])
async def read_picks(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Pick).offset(skip).limit(limit))
    picks = result.scalars().all()
    return picks

@router.get("/{pick_id}", response_model=schemas.Pick)
async def read_pick(pick_id: int, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Pick).where(models.Pick.id == pick_id))
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
