import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.future import select
from .. import models, database
from ..ocr import pipeline, parser
from ..config import settings
import asyncio

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("SharpWatch bot active. Send pick screenshots to this group.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download photo, OCR it, save picks to DB, create notifications."""
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = bytes(await photo_file.download_as_bytearray())

        raw_text = pipeline.extract_text(photo_bytes)
        capper_name = parser.extract_capper_name(raw_text)
        picks = parser.parse_picks(raw_text)

        if not picks:
            logger.info("Telegram photo: no picks parsed")
            return

        async with database.AsyncSessionLocal() as session:
            # Resolve or create capper
            result = await session.execute(
                select(models.Capper).where(models.Capper.name == capper_name)
            )
            capper = result.scalars().first()
            if not capper:
                capper = models.Capper(name=capper_name or "Unknown")
                session.add(capper)
                await session.commit()
                await session.refresh(capper)

            for pick_data in picks:
                db_pick = models.Pick(
                    capper_id=capper.id,
                    sport=pick_data.get("sport", "Unknown"),
                    league=pick_data.get("league"),
                    match_key=pick_data.get("match_key"),
                    pick_text=pick_data.get("pick_text", ""),
                    units_risked=pick_data.get("units_risked", 1.0),
                    odds=pick_data.get("odds"),
                    result="PENDING",
                    profit=0.0,
                    raw_text=raw_text,
                )
                session.add(db_pick)
                await session.flush()  # get db_pick.id

                units_str = pick_data.get("units_risked", 1.0)
                notif_msg = f"New pick from {capper.name}: {pick_data.get('pick_text', '')} ({units_str}u)"
                notification = models.Notification(
                    pick_id=db_pick.id,
                    message=notif_msg,
                    read=False,
                )
                session.add(notification)

            await session.commit()

        logger.info(f"Telegram: saved {len(picks)} picks from {capper_name}")

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
