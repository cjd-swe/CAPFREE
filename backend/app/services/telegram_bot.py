import logging
import re
from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.future import select
from .. import models, database
from ..ocr import pipeline, parser
from ..config import settings
import asyncio

logger = logging.getLogger(__name__)

# Prefixes users commonly write before a capper name in the caption
_CAPTION_PREFIX_RE = re.compile(
    r"^(?:picks?\s+(?:from|by)|by|from|capper[:\s]+|via\s+)?",
    re.IGNORECASE,
)
# A "name-like" caption: short, starts with a word char, no pick markers
_PICK_MARKER_RE = re.compile(r"\b\d+(?:\.\d+)?u\b|\bover\b|\bunder\b|\bml\b", re.IGNORECASE)


def _extract_capper_from_caption(caption: Optional[str]) -> Optional[str]:
    """Try to pull a capper name from a Telegram photo caption."""
    if not caption:
        return None
    caption = caption.strip()
    # If the caption looks like pick content (has units/over/under), skip it
    if _PICK_MARKER_RE.search(caption):
        return None
    # Strip common prefixes ("picks from X", "by X", etc.)
    name = _CAPTION_PREFIX_RE.sub("", caption).strip()
    # Strip @-handle prefix if present
    name = re.sub(r"^@", "", name).strip()
    # Only accept reasonably short, non-empty strings as names
    if name and 2 <= len(name) <= 60:
        return name
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("SharpWatch bot active. Send pick screenshots to this group.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download photo, OCR it, save picks to DB, create notifications."""
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = bytes(await photo_file.download_as_bytearray())

        raw_text = pipeline.extract_text(photo_bytes)
        picks = parser.parse_picks(raw_text)

        if not picks:
            logger.info("Telegram photo: no picks parsed")
            return

        # Capper name priority:
        # 1. Caption text (user typed it alongside the photo)
        # 2. OCR-extracted from the image itself
        # 3. Sender's Telegram display name
        # 4. Fallback "Unknown"
        caption = update.message.caption
        sender_name = None
        if update.message.from_user:
            sender_name = update.message.from_user.full_name or update.message.from_user.username

        capper_name = (
            _extract_capper_from_caption(caption)
            or parser.extract_capper_name(raw_text)
            or sender_name
            or "Unknown"
        )
        logger.info(
            f"Telegram: capper resolved as '{capper_name}' "
            f"(caption={bool(_extract_capper_from_caption(caption))}, "
            f"ocr={bool(parser.extract_capper_name(raw_text))}, "
            f"sender={bool(sender_name)})"
        )

        async with database.AsyncSessionLocal() as session:
            # Resolve or create capper
            result = await session.execute(
                select(models.Capper).where(models.Capper.name == capper_name)
            )
            capper = result.scalars().first()
            if not capper:
                capper = models.Capper(name=capper_name)
                session.add(capper)
                await session.commit()
                await session.refresh(capper)

            # Use message send date as game_date — picks are typically for games later that day
            from datetime import timezone, timedelta
            msg_date = update.message.date
            if msg_date.tzinfo is not None:
                msg_date = msg_date.astimezone(timezone.utc).replace(tzinfo=None)

            # Fetch recent picks for this capper once (for duplicate checking)
            cutoff = datetime.utcnow() - timedelta(days=7)
            recent_result = await session.execute(
                select(models.Pick).where(
                    models.Pick.capper_id == capper.id,
                    models.Pick.date >= cutoff,
                )
            )
            recent_picks = recent_result.scalars().all()

            saved_count = 0
            skipped_count = 0

            for pick_data in picks:
                pick_text = pick_data.get("pick_text", "")
                norm_text = pick_text.strip().lower()

                is_dup = any(
                    p.pick_text.strip().lower() == norm_text and
                    (p.game_date or p.date).date() == msg_date.date()
                    for p in recent_picks
                )
                if is_dup:
                    logger.info(f"Telegram duplicate skipped: '{pick_text}' for {capper.name}")
                    skipped_count += 1
                    continue

                db_pick = models.Pick(
                    capper_id=capper.id,
                    sport=pick_data.get("sport", "Unknown"),
                    league=pick_data.get("league"),
                    match_key=pick_data.get("match_key"),
                    pick_text=pick_text,
                    units_risked=pick_data.get("units_risked", 1.0),
                    odds=pick_data.get("odds"),
                    result="PENDING",
                    profit=0.0,
                    raw_text=raw_text,
                    game_date=msg_date,
                )
                session.add(db_pick)
                await session.flush()  # get db_pick.id

                units_str = pick_data.get("units_risked", 1.0)
                notif_msg = f"New pick from {capper.name}: {pick_text} ({units_str}u)"
                notification = models.Notification(
                    pick_id=db_pick.id,
                    message=notif_msg,
                    read=False,
                )
                session.add(notification)
                saved_count += 1

            await session.commit()

        logger.info(f"Telegram: saved {saved_count} picks, skipped {skipped_count} duplicates from {capper_name}")

        # Also save to queue for record-keeping
        async with database.AsyncSessionLocal() as session:
            queue_item = models.TelegramQueue(
                message_id=str(update.message.message_id),
                chat_id=str(update.message.chat_id),
                photo_path="telegram_direct",
                processed=True,
            )
            session.add(queue_item)
            await session.commit()

    except Exception as e:
        logger.error(f"Telegram photo handler error: {e}")


def create_application() -> Application:
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == "your_token_here":
        return None
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return application


async def start_polling() -> None:
    """Start the Telegram bot in polling mode (for local dev)."""
    app = create_application()
    if app is None:
        logger.info("Telegram bot token not configured — skipping bot startup")
        return
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot polling started")
        # Keep running until cancelled
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
    except Exception as e:
        logger.error(f"Telegram bot error: {e}")
