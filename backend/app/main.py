import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import picks, upload, telegram, analytics, settings, notifications
from .config import settings as app_settings

app = FastAPI(title="SharpWatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if app_settings.TELEGRAM_BOT_TOKEN and app_settings.TELEGRAM_BOT_TOKEN != "your_token_here":
        from .services.telegram_bot import start_polling
        asyncio.create_task(start_polling())


app.include_router(picks.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(telegram.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Welcome to SharpWatch API"}
