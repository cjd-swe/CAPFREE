from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from .. import models, schemas, database

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


@router.get("/", response_model=List[schemas.Notification])
async def get_notifications(db: AsyncSession = Depends(database.get_db)):
    """Get last 20 notifications ordered by created_at desc"""
    result = await db.execute(
        select(models.Notification)
        .order_by(models.Notification.created_at.desc())
        .limit(20)
    )
    return result.scalars().all()


@router.get("/unread-count")
async def get_unread_count(db: AsyncSession = Depends(database.get_db)):
    """Get count of unread notifications"""
    from sqlalchemy import func
    result = await db.execute(
        select(func.count(models.Notification.id))
        .where(models.Notification.read == False)
    )
    count = result.scalar() or 0
    return {"count": count}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: int, db: AsyncSession = Depends(database.get_db)):
    """Mark a single notification as read"""
    result = await db.execute(
        select(models.Notification).where(models.Notification.id == notification_id)
    )
    notif = result.scalars().first()
    if notif:
        notif.read = True
        await db.commit()
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(db: AsyncSession = Depends(database.get_db)):
    """Mark all notifications as read"""
    result = await db.execute(
        select(models.Notification).where(models.Notification.read == False)
    )
    notifs = result.scalars().all()
    for n in notifs:
        n.read = True
    await db.commit()
    return {"ok": True, "marked": len(notifs)}
