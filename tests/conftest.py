# --- FEATURE[apple_pay] START ---
from tests.apple_pay_credentials import ensure_apple_pay_test_credentials

ensure_apple_pay_test_credentials()

# --- FEATURE[apple_pay] END ---
from typing import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
from faker import Faker  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402
from sqlalchemy.sql import text  # noqa: E402
from starlette.routing import Mount  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.db import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from tests.sample_model import (  # noqa: E402
    SampleRecord,
    SampleRecordRepo,
    sample_record_data,
)


def mounted_apps() -> list[FastAPI]:
    """The root app and every FastAPI sub-app mounted on it (the versioned APIs).

    A mounted sub-app resolves its own dependencies, so an override set only on
    the root app does not reach the versioned routes.
    """
    sub_apps = [route.app for route in app.routes if isinstance(route, Mount) and isinstance(route.app, FastAPI)]
    return [app, *sub_apps]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def test_app() -> AsyncGenerator[FastAPI, None]:
    """Create a FastAPI test application with an async database session."""
    # Override the database settings for testing.
    # NullPool + explicit dispose() below: this engine is created fresh per test
    # function, so it must not leave pooled connections behind - otherwise the
    # suite accumulates open Postgres connections across hundreds of tests and
    # intermittently hits max_connections (worse under CI's tighter/variable
    # resource conditions than a local dev machine).
    test_engine = create_async_engine(settings.db_test_url.human_repr(), echo=False, poolclass=NullPool)

    try:
        # Create test engine and override the get_session dependency
        test_async_session = async_sessionmaker(test_engine, expire_on_commit=False)

        # Create schema and tables
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            # Create schema if it doesn't exist
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.postgres_db_schema}"'))
            await conn.run_sync(Base.metadata.create_all)

        async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
            async with test_async_session() as session:
                yield session

        for mounted_app in mounted_apps():
            mounted_app.dependency_overrides[get_session] = override_get_session

        yield app

        # Clean up
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{settings.postgres_db_schema}"'))

        # Clear any application dependencies
        for mounted_app in mounted_apps():
            mounted_app.dependency_overrides.clear()
    finally:
        await test_engine.dispose()


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    # base_url's host must be in ALLOWED_HOSTS (see .env.example) so the
    # TrustedHostMiddleware on the app lets test requests through.
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://localhost") as ac:
        yield ac


@pytest.fixture
async def faker() -> Faker:
    """Create a Faker instance for generating test data."""
    return Faker()


@pytest.fixture
async def db_session(test_app: FastAPI) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for a test."""
    # NullPool + dispose(): see test_app fixture above for why this matters.
    test_engine = create_async_engine(settings.db_test_url.human_repr(), poolclass=NullPool)
    test_async_session = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    try:
        async with test_async_session() as session:
            yield session
            await session.rollback()
    finally:
        await test_engine.dispose()


@pytest.fixture
async def sample_record(db_session: AsyncSession, faker: Faker) -> SampleRecord:
    """A stored row of the test-only model (see tests/sample_model.py)."""
    return await SampleRecordRepo(db_session).create_one(sample_record_data(faker))
