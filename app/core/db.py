from typing import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Create async database engine
engine = create_async_engine(
    settings.db_url.human_repr(),
    echo=settings.db_echo,
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


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session_factory = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=engine,
        class_=AsyncSession,
    )

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
