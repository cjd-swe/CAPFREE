import asyncio
import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .auth import router as auth_router, require_auth
from .routers import picks, upload, telegram, analytics, settings, notifications
from .config import settings as app_settings

logger = logging.getLogger(__name__)

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
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema ready")
    except Exception as exc:
        logger.error("DB init failed — app will start but DB calls will fail: %s", exc)

    if app_settings.TELEGRAM_BOT_TOKEN and app_settings.TELEGRAM_BOT_TOKEN != "your_token_here":
        from .services.telegram_bot import start_polling
        asyncio.create_task(start_polling())


# Auth routes are public (login/logout/me)
app.include_router(auth_router, prefix="/api")

# All other routes require auth (no-op when APP_PASSWORD is empty)
app.include_router(picks.router, prefix="/api", dependencies=[Depends(require_auth)])
app.include_router(upload.router, prefix="/api", dependencies=[Depends(require_auth)])
app.include_router(telegram.router, prefix="/api", dependencies=[Depends(require_auth)])
app.include_router(analytics.router, prefix="/api", dependencies=[Depends(require_auth)])
app.include_router(settings.router, prefix="/api", dependencies=[Depends(require_auth)])
app.include_router(notifications.router, prefix="/api", dependencies=[Depends(require_auth)])


@app.get("/")
async def root():
    return {"message": "Welcome to SharpWatch API"}
