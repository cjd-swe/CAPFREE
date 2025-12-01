from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.future import select
from .. import models, database
from ..ocr import pipeline, parser
import os
import io

# Placeholder for token - should be in env vars
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN_HERE")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hi! Send me a screenshot of your picks.')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    # Save to queue
    async with database.AsyncSessionLocal() as session:
        queue_item = models.TelegramQueue(
            message_id=str(update.message.message_id),
            chat_id=str(update.message.chat_id),
            photo_path="memory", # In real app, save to S3 or disk
            processed=False
        )
        session.add(queue_item)
        await session.commit()
    
    # Process immediately for demo
    raw_text = pipeline.extract_text(bytes(photo_bytes))
    picks = parser.parse_picks(raw_text)
    
    response = "Parsed Picks:\n"
    for pick in picks:
        response += f"- {pick['pick_text']} ({pick['units_risked']}u)\n"
    
    await update.message.reply_text(response)

def create_application():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return application
