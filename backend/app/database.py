import os

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SQLITE_URL = f"sqlite+aiosqlite:///{os.path.join(BASE_DIR, 'sharpwatch.db')}"


def resolve_database_url(raw: str = "") -> str:
    """
    Normalise a database URL so it can be handed to SQLAlchemy's async engine.

    - Empty string → local SQLite file (backend/sharpwatch.db).
    - `postgres://...` → `postgresql://...` (Heroku-style aliases).
    - `postgresql://...` → `postgresql+asyncpg://...` so SQLAlchemy picks the
      asyncpg driver. Hosting providers (Supabase, Render, Railway) hand out
      plain `postgresql://` URLs, so callers can paste them verbatim.
    - Any URL that already names a driver (e.g. `postgresql+asyncpg://...`,
      `sqlite+aiosqlite://...`) is returned untouched.
    """
    raw = (raw or "").strip()
    if not raw:
        return DEFAULT_SQLITE_URL
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]
    if raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[len("postgresql://"):]
    return raw


DATABASE_URL = resolve_database_url(settings.DATABASE_URL)

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
