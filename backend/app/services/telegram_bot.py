import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, TypeHandler, filters, ContextTypes

from .. import models, database
from ..config import settings
from ..ocr import parse_router, parser

logger = logging.getLogger(__name__)

# Runtime state exposed via GET /api/telegram/status so the UI can show
# whether the bot is actually receiving anything.
bot_state = {
    "polling_running": False,
    "started_at": None,      # datetime | None
    "last_error": None,      # str | None
    "last_update_at": None,  # datetime | None
}


def _extract_forward_name(msg) -> Optional[str]:
    """Get the original sender's display name from a forwarded message.

    PTB v21 removed `Message.forward_from` / `forward_sender_name` in favor of
    `forward_origin` — accessing the old attributes raises AttributeError,
    which used to crash the photo handler on every message. Handle both APIs.
    """
    origin = getattr(msg, "forward_origin", None)
    if origin is not None:
        sender_user = getattr(origin, "sender_user", None)  # MessageOriginUser
        if sender_user is not None:
            return sender_user.full_name or sender_user.username
        hidden_name = getattr(origin, "sender_user_name", None)  # MessageOriginHiddenUser
        if hidden_name:
            return hidden_name
        # MessageOriginChat / MessageOriginChannel
        chat = getattr(origin, "sender_chat", None) or getattr(origin, "chat", None)
        if chat is not None:
            return chat.title or getattr(chat, "username", None)
        return None
    # Pre-v21 PTB fallback
    fwd_user = getattr(msg, "forward_from", None)
    if fwd_user is not None:
        return fwd_user.full_name or fwd_user.username
    return getattr(msg, "forward_sender_name", None)


def _describe_message(msg) -> tuple[str, Optional[str]]:
    """Classify a Telegram message and pull its display text."""
    if msg.photo:
        return "photo", msg.caption
    if msg.document:
        return "document", msg.caption or msg.document.file_name
    if msg.text:
        if msg.text.startswith("/"):
            return "command", msg.text
        return "text", msg.text
    return "other", msg.caption


async def record_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log every incoming update to telegram_messages (runs before handlers).

    This is the visibility layer: if a message you sent to the group never
    shows up here, Telegram didn't deliver it to the bot at all — check
    privacy mode (@BotFather /setprivacy) and that the bot is in the chat.
    """
    bot_state["last_update_at"] = datetime.utcnow()
    msg = update.effective_message
    if msg is None:
        return
    try:
        msg_type, text = _describe_message(msg)
        sender = None
        if msg.from_user:
            sender = msg.from_user.full_name or msg.from_user.username
        async with database.AsyncSessionLocal() as session:
            session.add(models.TelegramMessage(
                message_id=str(msg.message_id),
                chat_id=str(msg.chat_id),
                chat_title=getattr(msg.chat, "title", None),
                sender_name=sender,
                message_type=msg_type,
                text=(text or "")[:1000] or None,
                status="received",
            ))
            await session.commit()
    except Exception:
        logger.exception("Telegram: failed to record incoming message")


async def _set_message_status(
    update: Update,
    status: str,
    detail: Optional[str] = None,
    picks_saved: int = 0,
) -> None:
    """Update the audit row created by record_update with the outcome."""
    msg = update.effective_message
    if msg is None:
        return
    try:
        async with database.AsyncSessionLocal() as session:
            result = await session.execute(
                select(models.TelegramMessage)
                .where(
                    models.TelegramMessage.chat_id == str(msg.chat_id),
                    models.TelegramMessage.message_id == str(msg.message_id),
                )
                .order_by(models.TelegramMessage.id.desc())
            )
            row = result.scalars().first()
            if row is None:
                return
            row.status = status
            row.detail = detail
            row.picks_saved = picks_saved
            await session.commit()
    except Exception:
        logger.exception("Telegram: failed to update message status")

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
    await _set_message_status(update, "not_parsed", "Bot command")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Text messages aren't parsed for picks — record them so they're visible."""
    await _set_message_status(
        update,
        "not_parsed",
        "Text messages aren't parsed — send pick screenshots as photos",
    )


async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all for unsupported message types (video, audio, non-image files)."""
    await _set_message_status(
        update,
        "not_parsed",
        "Unsupported message type — send pick screenshots as photos or image files",
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download photo, OCR it, save picks to DB, create notifications."""
    try:
        # Screenshots arrive either as compressed photos or as uncompressed
        # image documents ("send as file") — accept both.
        if update.message.photo:
            tg_file = await update.message.photo[-1].get_file()
        else:
            tg_file = await update.message.document.get_file()
        photo_bytes = bytes(await tg_file.download_as_bytearray())

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
                await _set_message_status(
                    update, "no_picks",
                    "OCR was unreliable and vision found no picks — upload this "
                    "screenshot manually via the Upload page",
                )
            else:
                logger.info(
                    "Telegram photo message_id=%s: no picks parsed (engine=%s)",
                    update.message.message_id,
                    engine,
                )
                await _set_message_status(
                    update, "no_picks", f"No picks parsed from image (engine={engine})",
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

        forward_name = _extract_forward_name(update.message)

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
            # Resolve or create capper. Updates are processed sequentially by
            # default, but guard against the unique-name race anyway (e.g. if
            # concurrent_updates is ever enabled, or a manual upload for the
            # same new capper lands at the same moment).
            result = await session.execute(
                select(models.Capper).where(models.Capper.name == capper_name)
            )
            capper = result.scalars().first()
            if not capper:
                capper = models.Capper(name=capper_name)
                session.add(capper)
                try:
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                    result = await session.execute(
                        select(models.Capper).where(models.Capper.name == capper_name)
                    )
                    capper = result.scalars().first()
                    if not capper:
                        raise
                else:
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
            failed_count = 0

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

                # Each pick gets its own SAVEPOINT so a bad row (e.g. a field
                # that fails a DB constraint) only loses that one pick instead
                # of rolling back every other pick already staged in this
                # message's batch.
                try:
                    async with session.begin_nested():
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
                except Exception:
                    logger.exception(
                        f"Telegram: failed to save pick '{pick_text}' for {capper.name}"
                    )
                    failed_count += 1
                    continue
                saved_count += 1

            if failed_count:
                # Surface the failure in-app — otherwise it's only visible by
                # digging through server logs.
                session.add(models.Notification(
                    pick_id=None,
                    message=(
                        f"{failed_count} pick(s) from {capper.name} failed to save "
                        f"— check server logs for details"
                    ),
                    read=False,
                ))

            await session.commit()

        logger.info(
            f"Telegram: saved {saved_count} picks, skipped {skipped_count} duplicates, "
            f"failed {failed_count} from {capper_name}"
        )

        outcome_bits = [f"{saved_count} pick(s) saved for {capper_name}"]
        if skipped_count:
            outcome_bits.append(f"{skipped_count} duplicate(s) skipped")
        if failed_count:
            outcome_bits.append(f"{failed_count} failed — check server logs")
        await _set_message_status(
            update, "saved_picks", ", ".join(outcome_bits), picks_saved=saved_count,
        )

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

    except Exception as exc:
        logger.exception("Telegram photo handler error")
        await _set_message_status(
            update, "error", f"Processing failed: {str(exc)[:300]}",
        )


def create_application() -> Application:
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == "your_token_here":
        return None
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    # Group -1 runs before the group-0 handlers and records *every* update,
    # even types no other handler processes.
    application.add_handler(TypeHandler(Update, record_update), group=-1)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(
        MessageHandler(
            filters.ALL & ~filters.PHOTO & ~filters.Document.IMAGE & ~filters.TEXT,
            handle_other,
        )
    )
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
        # Keep pending updates: messages sent while the backend was down or
        # asleep are processed on wake instead of being silently discarded.
        await app.updater.start_polling(drop_pending_updates=False)
        bot_state["polling_running"] = True
        bot_state["started_at"] = datetime.utcnow()
        bot_state["last_error"] = None
        logger.info("Telegram bot polling started")
        # Keep running until cancelled
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        bot_state["polling_running"] = False
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
    except Exception as e:
        bot_state["polling_running"] = False
        bot_state["last_error"] = str(e)
        logger.error(f"Telegram bot error: {e}")
