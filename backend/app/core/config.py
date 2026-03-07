from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://dorkraptor:dorkraptor@postgres:5432/dorkraptor"
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    OPENAI_API_KEY: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None

    SECRET_KEY: str = "dorkraptor-secret-key-change-in-production"
    DEBUG: bool = False

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None

    # Rate limiting
    SEARCH_DELAY_MIN: float = 2.0
    SEARCH_DELAY_MAX: float = 5.0
    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 15

    ENABLED_ENGINES: str = "bing,duckduckgo"
    SEARCH_CONCURRENCY: int = 3
    RESULTS_PER_ENGINE: int = 10

    CACHE_BACKEND: str = "memory"
    CACHE_TTL_SECONDS: int = 3600
    CACHE_MAX_MEMORY_ENTRIES: int = 2000

    HTTP_PROXY: Optional[str] = None

    class Config:
        env_file = ".env"

    @property
    def enabled_engines_list(self) -> List[str]:
        return [e.strip().lower() for e in self.ENABLED_ENGINES.split(",") if e.strip()]


settings = Settings()
