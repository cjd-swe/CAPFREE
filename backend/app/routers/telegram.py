import logging
from typing import List

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from telegram import Bot, Update

from .. import database, models, schemas
from ..config import settings
from ..services.telegram_bot import bot_state, create_application

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/telegram",
    tags=["telegram"],
)

application = create_application()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    if application is None:
        return {"status": "bot not configured"}
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}


@router.get("/status", response_model=schemas.TelegramStatus)
async def telegram_status(db: AsyncSession = Depends(database.get_db)):
    """Health check for the Telegram integration.

    `can_read_all_group_messages` is the key field: when False, BotFather
    privacy mode is on and the bot never receives regular group messages —
    which looks exactly like "my messages aren't showing up".
    """
    token = settings.TELEGRAM_BOT_TOKEN
    configured = bool(token) and token != "your_token_here"

    count_result = await db.execute(
        select(func.count()).select_from(models.TelegramMessage)
    )
    messages_recorded = count_result.scalar() or 0

    status = schemas.TelegramStatus(
        configured=configured,
        polling_running=bot_state["polling_running"],
        polling_started_at=bot_state["started_at"],
        last_error=bot_state["last_error"],
        last_update_at=bot_state["last_update_at"],
        messages_recorded=messages_recorded,
    )
    if not configured:
        return status

    try:
        async with Bot(token) as bot:
            me = await bot.get_me()
        status.connected = True
        status.bot_username = me.username
        status.can_read_all_group_messages = me.can_read_all_group_messages
    except Exception as exc:
        logger.warning("Telegram getMe failed: %s", exc)
        status.last_error = status.last_error or f"getMe failed: {exc}"
    return status


@router.get("/messages", response_model=List[schemas.TelegramMessage])
async def telegram_messages(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(database.get_db),
):
    """Recent messages the bot has received, newest first."""
    result = await db.execute(
        select(models.TelegramMessage)
        .order_by(models.TelegramMessage.id.desc())
        .limit(limit)
    )
    return result.scalars().all()
