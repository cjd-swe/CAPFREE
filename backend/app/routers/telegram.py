from fastapi import APIRouter, Request
from telegram import Update
from ..services.telegram_bot import create_application

router = APIRouter(
    prefix="/telegram",
    tags=["telegram"],
)

application = create_application()

@router.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}
