from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from .config import settings


def resolve_database_url(raw: str = "") -> str:
    """
    Normalise a database URL so it can be handed to SQLAlchemy's async engine.

    Requires a valid DATABASE_URL — there is no local fallback.

    - `postgres://...` → `postgresql://...` (Heroku-style aliases).
    - `postgresql://...` → `postgresql+asyncpg://...` so SQLAlchemy picks the
      asyncpg driver. Hosting providers (Supabase, Render, Railway) hand out
      plain `postgresql://` URLs, so callers can paste them verbatim.
    - Any URL that already names a driver (e.g. `postgresql+asyncpg://...`)
      is returned untouched.
    """
    raw = (raw or "").strip()
    if not raw:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to backend/.env — "
            "see .env.example for Supabase connection string format."
        )
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]
    if raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[len("postgresql://"):]
    return raw


DATABASE_URL = resolve_database_url(settings.DATABASE_URL)

# Supabase's transaction pooler (port 6543, "pooler.supabase.com") runs
# pgbouncer in transaction mode. Each transaction may land on a different
# backend, so prepared statements can't be reused and their auto-generated
# names collide. Fix: let pgbouncer do the pooling (NullPool on our side),
# disable asyncpg's own statement cache, and give prepared statements unique
# names per connection so two asyncpg connections that happen to hit the
# same backend don't clash.
_is_pgbouncer = ":6543" in DATABASE_URL or "pooler." in DATABASE_URL

if _is_pgbouncer:
    import uuid
    engine = create_async_engine(
        DATABASE_URL,
        echo=True,
        poolclass=NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
        },
    )
else:
    engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
