from fastapi import APIRouter, Depends, HTTPException
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

@router.get("/capper/{capper_id}")
async def get_capper_analytics(capper_id: int, db: AsyncSession = Depends(database.get_db)):
    """Get detailed analytics for a specific capper"""
    # Get capper
    result = await db.execute(select(models.Capper).where(models.Capper.id == capper_id))
    capper = result.scalars().first()
    if capper is None:
        raise HTTPException(status_code=404, detail="Capper not found")
    
    # Get all picks for this capper
    result = await db.execute(
        select(models.Pick)
        .where(models.Pick.capper_id == capper_id)
        .order_by(models.Pick.date.desc())
    )
    picks = result.scalars().all()
    
    # Calculate statistics
    total_picks = len(picks)
    wins = sum(1 for p in picks if p.result == "WIN")
    losses = sum(1 for p in picks if p.result == "LOSS")
    pushes = sum(1 for p in picks if p.result == "PUSH")
    pending = sum(1 for p in picks if p.result == "PENDING")
    
    total_profit = sum(p.profit for p in picks)
    total_units = sum(p.units_risked for p in picks)
    
    win_rate = (wins / total_picks * 100) if total_picks > 0 else 0
    roi = (total_profit / total_units * 100) if total_units > 0 else 0
    
    # Get recent picks (last 10)
    recent_picks = picks[:10]
    
    # Performance by sport
    sport_performance = {}
    for pick in picks:
        if pick.sport not in sport_performance:
            sport_performance[pick.sport] = {
                "wins": 0,
                "losses": 0,
                "pushes": 0,
                "profit": 0.0,
                "total": 0
            }
        sport_performance[pick.sport]["total"] += 1
        sport_performance[pick.sport]["profit"] += pick.profit
        if pick.result == "WIN":
            sport_performance[pick.sport]["wins"] += 1
        elif pick.result == "LOSS":
            sport_performance[pick.sport]["losses"] += 1
        elif pick.result == "PUSH":
            sport_performance[pick.sport]["pushes"] += 1
    
    return {
        "id": capper.id,
        "name": capper.name,
        "total_picks": total_picks,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "pending": pending,
        "win_rate": round(win_rate, 1),
        "roi": round(roi, 1),
        "total_profit": round(total_profit, 2),
        "total_units_risked": round(total_units, 2),
        "recent_picks": recent_picks,
        "sport_performance": sport_performance
    }

@router.get("/daily-profit")
async def get_daily_profit(days: int = 30, db: AsyncSession = Depends(database.get_db)):
    """Get daily profit for the last N days"""
    # Calculate date threshold
    from datetime import datetime, timedelta
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get picks from start_date
    result = await db.execute(
        select(models.Pick)
        .where(models.Pick.date >= start_date)
        .order_by(models.Pick.date)
    )
    picks = result.scalars().all()
    
    # Group by date
    daily_data = {}
    cumulative_profit = 0.0
    
    # Initialize all dates in range with 0 profit
    for i in range(days + 1):
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        daily_data[date] = 0.0
        
    for pick in picks:
        date_str = pick.date.strftime("%Y-%m-%d")
        if date_str in daily_data:
            daily_data[date_str] += pick.profit
            
    # Format for chart
    chart_data = []
    for date, profit in sorted(daily_data.items()):
        # Format date as "Mon DD" or similar for chart
        dt = datetime.strptime(date, "%Y-%m-%d")
        formatted_date = dt.strftime("%b %d")
        
        chart_data.append({
            "name": formatted_date,
            "profit": round(profit, 2),
            "date": date
        })
        
    return chart_data

@router.get("/sport-performance")
async def get_sport_performance(db: AsyncSession = Depends(database.get_db)):
    """Get performance metrics by sport"""
    result = await db.execute(select(models.Pick))
    picks = result.scalars().all()
    
    sport_stats = {}
    
    for pick in picks:
        sport = pick.sport or "Unknown"
        if sport not in sport_stats:
            sport_stats[sport] = {
                "name": sport,
                "wins": 0,
                "losses": 0,
                "pushes": 0,
                "total": 0,
                "profit": 0.0,
                "units": 0.0
            }
            
        sport_stats[sport]["total"] += 1
        sport_stats[sport]["profit"] += pick.profit
        sport_stats[sport]["units"] += pick.units_risked
        
        if pick.result == "WIN":
            sport_stats[sport]["wins"] += 1
        elif pick.result == "LOSS":
            sport_stats[sport]["losses"] += 1
        elif pick.result == "PUSH":
            sport_stats[sport]["pushes"] += 1
            
    # Calculate rates and format
    formatted_stats = []
    for sport, stats in sport_stats.items():
        win_rate = (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0
        roi = (stats["profit"] / stats["units"] * 100) if stats["units"] > 0 else 0
        
        formatted_stats.append({
            "name": sport,
            "value": round(win_rate, 1), # For pie chart
            "win_rate": round(win_rate, 1),
            "roi": round(roi, 1),
            "profit": round(stats["profit"], 2),
            "total_picks": stats["total"],
            "record": f"{stats['wins']}-{stats['losses']}-{stats['pushes']}"
        })
        
    # Sort by total picks
    formatted_stats.sort(key=lambda x: x["total_picks"], reverse=True)
    
    return formatted_stats
