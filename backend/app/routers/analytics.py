from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import Dict, Any
from datetime import datetime, timedelta
from .. import models, database

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(database.get_db)) -> Dict[str, Any]:
    """Get summary statistics"""
    result = await db.execute(select(func.sum(models.Pick.profit)))
    total_profit = result.scalar() or 0.0

    result = await db.execute(select(func.count(models.Pick.id)))
    total_picks = result.scalar() or 0

    result = await db.execute(
        select(func.count(models.Pick.id)).where(models.Pick.result == "WIN")
    )
    wins = result.scalar() or 0

    result = await db.execute(
        select(func.count(models.Pick.id)).where(models.Pick.result == "PENDING")
    )
    pending_picks = result.scalar() or 0

    result = await db.execute(select(func.sum(models.Pick.units_risked)))
    total_units = result.scalar() or 1.0

    win_rate = (wins / total_picks * 100) if total_picks > 0 else 0
    roi = (total_profit / total_units * 100) if total_units > 0 else 0

    result = await db.execute(select(func.count(func.distinct(models.Capper.id))))
    active_cappers = result.scalar() or 0

    return {
        "total_profit": round(total_profit, 2),
        "win_rate": round(win_rate, 1),
        "roi": round(roi, 1),
        "active_cappers": active_cappers,
        "total_picks": total_picks,
        "pending_picks": pending_picks,
    }


@router.get("/cappers")
async def get_cappers_stats(db: AsyncSession = Depends(database.get_db)):
    """Get capper leaderboard"""
    result = await db.execute(select(models.Capper))
    cappers = result.scalars().all()

    capper_stats = []
    for capper in cappers:
        result = await db.execute(
            select(models.Pick).where(models.Pick.capper_id == capper.id)
        )
        picks = result.scalars().all()

        if not picks:
            continue

        total_profit = sum(p.profit for p in picks)
        total_units = sum(p.units_risked for p in picks)
        wins = sum(1 for p in picks if p.result == "WIN")
        losses = sum(1 for p in picks if p.result == "LOSS")
        pushes = sum(1 for p in picks if p.result == "PUSH")
        pending = sum(1 for p in picks if p.result == "PENDING")
        total = len(picks)

        # Confirmed wins: espn_api + manual only
        confirmed_wins = sum(
            1 for p in picks
            if p.result == "WIN" and p.grade_source in ("espn_api", "manual")
        )
        # Total wins including auto_win
        total_wins = wins

        graded_total = total - pending
        confirmed_win_rate = (confirmed_wins / graded_total * 100) if graded_total > 0 else 0
        total_win_rate = (total_wins / graded_total * 100) if graded_total > 0 else 0
        roi = (total_profit / total_units * 100) if total_units > 0 else 0

        # Current streak — walk backwards through graded picks
        graded_picks = [p for p in picks if p.result in ("WIN", "LOSS", "PUSH")]
        graded_picks.sort(key=lambda p: p.game_date or p.date, reverse=True)
        streak = 0
        streak_type = None
        for p in graded_picks:
            r = p.result
            if streak_type is None:
                streak_type = r
            if r == streak_type:
                streak += 1
            else:
                break
        # Encode: positive = win streak, negative = loss streak, 0 = no picks
        if streak_type == "WIN":
            current_streak = streak
        elif streak_type == "LOSS":
            current_streak = -streak
        else:
            current_streak = 0  # PUSH streak — treat as neutral

        capper_stats.append({
            "id": capper.id,
            "name": capper.name,
            "profit": round(total_profit, 2),
            "roi": round(roi, 1),
            "win_rate": round(total_win_rate, 1),
            "confirmed_win_rate": round(confirmed_win_rate, 1),
            "total_win_rate": round(total_win_rate, 1),
            "total_picks": total,
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "pending": pending,
            "current_streak": current_streak,
        })

    capper_stats.sort(key=lambda x: x["profit"], reverse=True)
    return capper_stats


@router.get("/capper/{capper_id}")
async def get_capper_analytics(capper_id: int, db: AsyncSession = Depends(database.get_db)):
    """Get detailed analytics for a specific capper"""
    result = await db.execute(select(models.Capper).where(models.Capper.id == capper_id))
    capper = result.scalars().first()
    if capper is None:
        raise HTTPException(status_code=404, detail="Capper not found")

    result = await db.execute(
        select(models.Pick)
        .where(models.Pick.capper_id == capper_id)
        .order_by(models.Pick.date.desc())
    )
    picks = result.scalars().all()

    total_picks = len(picks)
    wins = sum(1 for p in picks if p.result == "WIN")
    losses = sum(1 for p in picks if p.result == "LOSS")
    pushes = sum(1 for p in picks if p.result == "PUSH")
    pending = sum(1 for p in picks if p.result == "PENDING")

    total_profit = sum(p.profit for p in picks)
    total_units = sum(p.units_risked for p in picks)

    win_rate = (wins / total_picks * 100) if total_picks > 0 else 0
    roi = (total_profit / total_units * 100) if total_units > 0 else 0

    recent_picks = picks[:10]

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
        "notes": capper.notes,
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


@router.get("/capper/{capper_id}/profit-history")
async def get_capper_profit_history(capper_id: int, db: AsyncSession = Depends(database.get_db)):
    """Get profit-over-time history for a capper"""
    result = await db.execute(select(models.Capper).where(models.Capper.id == capper_id))
    capper = result.scalars().first()
    if capper is None:
        raise HTTPException(status_code=404, detail="Capper not found")

    result = await db.execute(
        select(models.Pick)
        .where(
            models.Pick.capper_id == capper_id,
            models.Pick.result != "PENDING"
        )
        .order_by(models.Pick.date.asc())
    )
    picks = result.scalars().all()

    history = []
    cumulative = 0.0
    for pick in picks:
        cumulative += pick.profit
        history.append({
            "date": (pick.game_date or pick.date).strftime("%Y-%m-%d"),
            "date_added": pick.date.strftime("%Y-%m-%d"),
            "pick_text": pick.pick_text,
            "result": pick.result,
            "grade_source": pick.grade_source,
            "profit": round(pick.profit, 2),
            "cumulative_profit": round(cumulative, 2),
            "sport": pick.sport,
            "units_risked": pick.units_risked,
        })

    return history


@router.get("/daily-profit")
async def get_daily_profit(days: int = 30, db: AsyncSession = Depends(database.get_db)):
    """Get daily profit for the last N days"""
    start_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(models.Pick)
        .where(models.Pick.date >= start_date)
        .order_by(models.Pick.date)
    )
    picks = result.scalars().all()

    daily_data = {}
    for i in range(days + 1):
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        daily_data[date] = 0.0

    for pick in picks:
        date_str = pick.date.strftime("%Y-%m-%d")
        if date_str in daily_data:
            daily_data[date_str] += pick.profit

    chart_data = []
    for date, profit in sorted(daily_data.items()):
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

    formatted_stats = []
    for sport, stats in sport_stats.items():
        win_rate = (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0
        roi = (stats["profit"] / stats["units"] * 100) if stats["units"] > 0 else 0

        formatted_stats.append({
            "name": sport,
            "value": round(win_rate, 1),
            "win_rate": round(win_rate, 1),
            "roi": round(roi, 1),
            "profit": round(stats["profit"], 2),
            "total_picks": stats["total"],
            "record": f"{stats['wins']}-{stats['losses']}-{stats['pushes']}"
        })

    formatted_stats.sort(key=lambda x: x["total_picks"], reverse=True)
    return formatted_stats
