from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from .. import models, schemas, database

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)

@router.get("/cappers", response_model=List[schemas.Capper])
async def get_all_cappers(db: AsyncSession = Depends(database.get_db)):
    """Get all cappers"""
    result = await db.execute(select(models.Capper).order_by(models.Capper.name))
    cappers = result.scalars().all()
    return cappers

@router.post("/cappers", response_model=schemas.Capper, status_code=status.HTTP_201_CREATED)
async def create_capper(capper: schemas.CapperCreate, db: AsyncSession = Depends(database.get_db)):
    """Create a new capper"""
    # Check if capper with this name already exists
    result = await db.execute(select(models.Capper).where(models.Capper.name == capper.name))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Capper with this name already exists")
    
    db_capper = models.Capper(**capper.dict())
    db.add(db_capper)
    await db.commit()
    await db.refresh(db_capper)
    return db_capper

@router.patch("/cappers/{capper_id}", response_model=schemas.Capper)
async def update_capper(capper_id: int, capper_update: schemas.CapperUpdate, db: AsyncSession = Depends(database.get_db)):
    """Update a capper's information"""
    result = await db.execute(select(models.Capper).where(models.Capper.id == capper_id))
    db_capper = result.scalars().first()
    if db_capper is None:
        raise HTTPException(status_code=404, detail="Capper not found")
    
    # Check if new name conflicts with existing capper
    if capper_update.name and capper_update.name != db_capper.name:
        result = await db.execute(select(models.Capper).where(models.Capper.name == capper_update.name))
        existing = result.scalars().first()
        if existing:
            raise HTTPException(status_code=400, detail="Capper with this name already exists")
    
    update_data = capper_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_capper, key, value)
    
    await db.commit()
    await db.refresh(db_capper)
    return db_capper

@router.delete("/cappers/{capper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_capper(capper_id: int, db: AsyncSession = Depends(database.get_db)):
    """Delete a capper and all associated picks"""
    result = await db.execute(select(models.Capper).where(models.Capper.id == capper_id))
    db_capper = result.scalars().first()
    if db_capper is None:
        raise HTTPException(status_code=404, detail="Capper not found")
    
    # Delete associated picks first
    await db.execute(select(models.Pick).where(models.Pick.capper_id == capper_id))
    
    await db.delete(db_capper)
    await db.commit()
    return None
