from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker
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
}


def _init_enums_sync():
    """
    Use psycopg2 (synchronous) to safely create ENUM types.
    This runs before the async engine starts, avoiding all asyncpg/prepared-statement issues.
    """
    import psycopg2

    # Build a sync DSN from the async one
    sync_dsn = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql://"
    )

    conn = psycopg2.connect(sync_dsn)
    conn.autocommit = True
    cur = conn.cursor()

    for enum_name, enum_values in ENUM_DEFINITIONS.items():
        cur.execute("SELECT 1 FROM pg_type WHERE typname = %s", (enum_name,))
        if cur.fetchone() is None:
            values_sql = ", ".join(f"'{v}'" for v in enum_values)
            cur.execute(f"CREATE TYPE {enum_name} AS ENUM ({values_sql})")
            logger.info(f"Created ENUM type: {enum_name}")
        else:
            logger.info(f"ENUM type already exists, skipping: {enum_name}")

    cur.close()
    conn.close()


async def init_db():
    from app.models import scan, finding  # noqa: F401

    # Step 1: create ENUMs synchronously (safe, no prepared-statement issues)
    _init_enums_sync()

    # Step 2: create tables via SQLAlchemy (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully")


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
