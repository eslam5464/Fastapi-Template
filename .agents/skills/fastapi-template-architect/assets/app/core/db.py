# --- SNAPSHOT NOTICE (fastapi-template-architect skill) ---
# Verbatim copy of app/core/db.py from eslam5464/Fastapi-Template, taken 2026-11-06.
# The real repo is the source of truth; this is a fallback/reference copy
# for offline scaffolding and Extend/Audit-mode pattern-matching. It can drift
# from the live repo over time - prefer driving the real Copier template
# (see references/copier-template-mechanics.md) whenever that's available.
# --- END SNAPSHOT NOTICE ---

from typing import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Create async database engine
engine = create_async_engine(
    settings.db_url.human_repr(),
    echo=True if settings.debug else False,
    future=True,
    pool_pre_ping=True,
)

# Set pool size and max overflow for async engine
meta = MetaData(
    schema=settings.postgres_db_schema,
    naming_convention={
        "pk": "pk_%(table_name)s",
        "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
    },
)

SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
    class_=AsyncSession,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
