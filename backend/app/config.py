from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    # Comma-separated list of allowed CORS origins.
    # e.g. "http://localhost:3000,https://sharpwatch.example.com"
    CORS_ORIGINS: str = "http://localhost:3000"
    # Database connection URL (REQUIRED). Provider-style URLs
    # (`postgres://`, `postgresql://`) are normalised to
    # `postgresql+asyncpg://` automatically so you can paste what Supabase,
    # Render, or Railway give you verbatim.
    DATABASE_URL: str = ""
    # Shared password to access the app. Empty = auth disabled (open access).
    APP_PASSWORD: str = ""
    # Secret key for signing JWT tokens. Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    JWT_SECRET: str = "change-me-in-production"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
