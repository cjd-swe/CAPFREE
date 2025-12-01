from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import Dict, Any
from .. import models, database

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)

@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(database.get_db)) -> Dict[str, Any]:
    """Get summary statistics"""
    # Get total profit
    result = await db.execute(select(func.sum(models.Pick.profit)))
    total_profit = result.scalar() or 0.0
    
    # Get win count and total count
    result = await db.execute(select(func.count(models.Pick.id)))
    total_picks = result.scalar() or 0
    
    result = await db.execute(
        select(func.count(models.Pick.id)).where(models.Pick.result == "WIN")
    )
    wins = result.scalar() or 0
    
    # Get total units risked
    result = await db.execute(select(func.sum(models.Pick.units_risked)))
    total_units = result.scalar() or 1.0  # Avoid division by zero
    
    # Calculate metrics
    win_rate = (wins / total_picks * 100) if total_picks > 0 else 0
    roi = (total_profit / total_units * 100) if total_units > 0 else 0
    
    # Get active cappers count
    result = await db.execute(select(func.count(func.distinct(models.Capper.id))))
    active_cappers = result.scalar() or 0
    
    return {
        "total_profit": round(total_profit, 2),
        "win_rate": round(win_rate, 1),
        "roi": round(roi, 1),
        "active_cappers": active_cappers,
        "total_picks": total_picks,
    }

@router.get("/cappers")
async def get_cappers_stats(db: AsyncSession = Depends(database.get_db)):
    """Get capper leaderboard"""
    # Get all cappers with their picks
    result = await db.execute(select(models.Capper))
    cappers = result.scalars().all()
    
    capper_stats = []
    for capper in cappers:
        # Get picks for this capper
        result = await db.execute(
            select(models.Pick).where(models.Pick.capper_id == capper.id)
        )
        picks = result.scalars().all()
        
        if not picks:
            continue
        
        total_profit = sum(p.profit for p in picks)
        total_units = sum(p.units_risked for p in picks)
        wins = sum(1 for p in picks if p.result == "WIN")
        total = len(picks)
        
        win_rate = (wins / total * 100) if total > 0 else 0
        roi = (total_profit / total_units * 100) if total_units > 0 else 0
        
        capper_stats.append({
            "id": capper.id,
            "name": capper.name,
            "profit": round(total_profit, 2),
            "roi": f"{roi:.1f}%",
            "win_rate": f"{win_rate:.1f}%",
            "total_picks": total,
        })
    
    # Sort by profit descending
    capper_stats.sort(key=lambda x: x["profit"], reverse=True)
    
    return capper_stats
