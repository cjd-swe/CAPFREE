from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    # Comma-separated list of allowed CORS origins.
    # e.g. "http://localhost:3000,https://sharpwatch.example.com"
    CORS_ORIGINS: str = "http://localhost:3000"
    # Database connection URL. Empty string => fall back to local SQLite at
    # backend/sharpwatch.db (see database.py). Provider-style URLs
    # (`postgres://`, `postgresql://`) are normalised to
    # `postgresql+asyncpg://` automatically so you can paste what Supabase,
    # Render, or Railway give you verbatim.
    DATABASE_URL: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
