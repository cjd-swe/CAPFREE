import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.future import select
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from .. import models, database
from ..config import settings
from ..ocr import parse_router, parser

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


# Patterns that signal "picks by <name>" in the body of a forwarded post
_FORWARD_CAPPER_RE = re.compile(
    r"(?:picks?\s+(?:from|by)|plays?\s+(?:from|by)|by|from|capper[:\s]+|via\s+)@?([\w][\w\s.'\-]{1,50}?)(?:\s*[\n:]|$)",
    re.IGNORECASE,
)
_TRAILING_CAPPER_RE = re.compile(
    r"^@?([\w][\w\s.'\-]{1,50}?)(?:\s+picks?|\s+plays?|\s+card)\s*$",
    re.IGNORECASE,
)


def _extract_capper_from_forward_text(text: Optional[str]) -> Optional[str]:
    """Extract a capper name from the body of a forwarded Telegram post.

    Channel posts often open with 'Picks by CapperName' or a header line like
    'CapperName plays' — check the first line first, then the full text.
    """
    if not text:
        return None
    first_line = text.strip().splitlines()[0].strip()
    for src in (first_line, text.strip()):
        m = _FORWARD_CAPPER_RE.search(src)
        if m:
            name = m.group(1).strip().rstrip(":")
            if 2 <= len(name) <= 60:
                return name
    m = _TRAILING_CAPPER_RE.match(first_line)
    if m:
        name = m.group(1).strip()
        if 2 <= len(name) <= 60:
            return name
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("SharpWatch bot active. Send pick screenshots to this group.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download photo, OCR it, save picks to DB, create notifications."""
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = bytes(await photo_file.download_as_bytearray())

        parse_result = await parse_router.extract_picks(photo_bytes)
        picks = parse_result["picks"]
        raw_text = parse_result.get("raw_text", "")

        if not picks:
            engine = parse_result.get("engine")
            if engine == "vision_failed":
                logger.warning(
                    "Telegram photo message_id=%s: OCR was unreliable and vision "
                    "returned no picks — screenshot needs manual review",
                    update.message.message_id,
                )
            else:
                logger.info(
                    "Telegram photo message_id=%s: no picks parsed (engine=%s)",
                    update.message.message_id,
                    engine,
                )
            return

        # Capper name priority:
        # 1. Caption text (user typed it alongside the photo, no pick markers)
        # 2. Forwarded post text (e.g. "Picks by CapperName" in the channel post body)
        # 3. Forwarded-message metadata (original sender's Telegram display name)
        # 4. Vision/OCR-extracted from the image itself
        # 5. Sender's Telegram display name (whoever forwarded to us)
        # 6. Fallback "Unknown"
        caption = update.message.caption
        sender_name = None
        if update.message.from_user:
            sender_name = update.message.from_user.full_name or update.message.from_user.username

        forward_name = None
        if update.message.forward_from:
            forward_name = (
                update.message.forward_from.full_name
                or update.message.forward_from.username
            )
        elif update.message.forward_sender_name:
            # Privacy-protected accounts expose only a display name string
            forward_name = update.message.forward_sender_name

        caption_name = _extract_capper_from_caption(caption)
        forward_text_name = _extract_capper_from_forward_text(caption)

        capper_name = parse_router.clean_capper_name(
            caption_name
            or forward_text_name
            or forward_name
            or parse_result.get("capper_name")
            or sender_name
        ) or "Unknown"
        logger.info(
            f"Telegram: capper resolved as '{capper_name}' "
            f"(caption={bool(caption_name)}, "
            f"forward_text={bool(forward_text_name)}, "
            f"forward_meta={bool(forward_name)}, "
            f"ocr={bool(parse_result.get('capper_name'))}, "
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
