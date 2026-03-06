from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://dorkraptor:dorkraptor@postgres:5432/dorkraptor"
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    OPENAI_API_KEY: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None

    SECRET_KEY: str = "dorkraptor-secret-key-change-in-production"
    DEBUG: bool = False

    # Rate limiting
    SEARCH_DELAY_MIN: float = 2.0
    SEARCH_DELAY_MAX: float = 5.0
    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 15

    class Config:
        env_file = ".env"


settings = Settings()
