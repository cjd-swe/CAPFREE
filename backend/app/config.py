from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
