from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import text
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


ENUM_DEFINITIONS = {
    "scanstatus": ["pending", "running", "completed", "failed", "cancelled"],
    "severity": ["critical", "high", "medium", "low", "info"],
    "findingcategory": [
        "sensitive_files", "admin_panels", "directory_listings", "backup_files",
        "config_files", "credentials", "documents", "database_dumps",
        "cloud_storage", "github_leaks", "api_endpoints", "other"
    ],
    "findingsource": ["google", "bing", "duckduckgo", "yandex", "github", "cloud_scan"],
    "userrole": ["admin", "user"],
    "authprovider": ["local", "google"],
}


async def init_db():
    from app.models import scan, finding, user  # noqa: F401

    async with engine.begin() as conn:
        # Safely create ENUMs only if they don't already exist
        for enum_name, enum_values in ENUM_DEFINITIONS.items():
            result = await conn.execute(
                text("SELECT 1 FROM pg_type WHERE typname = :name"),
                {"name": enum_name}
            )
            if result.fetchone() is None:
                values_sql = ", ".join(f"'{v}'" for v in enum_values)
                await conn.execute(text(f"CREATE TYPE {enum_name} AS ENUM ({values_sql})"))
                logger.info(f"Created ENUM type: {enum_name}")
            else:
                logger.info(f"ENUM type already exists, skipping: {enum_name}")

        # Create tables — all model columns use create_type=False so no ENUM conflicts
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully")


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
