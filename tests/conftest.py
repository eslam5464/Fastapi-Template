# --- APPLE_PAY_TEST_CREDENTIALS_START ---
from tests.apple_pay_credentials import ensure_apple_pay_test_credentials

ensure_apple_pay_test_credentials()

# --- APPLE_PAY_TEST_CREDENTIALS_END ---
from typing import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
from faker import Faker  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from pwdlib import PasswordHash  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402
from sqlalchemy.sql import text  # noqa: E402

from app import repos  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.db import get_session  # noqa: E402
from app.main import app, v1_app, v2_app  # noqa: E402
from app.models import Base, User  # noqa: E402
from app.schemas import Token, UserCreate  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402

DEFAULT_PASSWORD = "P@ssword123"
_PASSWORD_HASH = PasswordHash.recommended()


@pytest.fixture(scope="session")
def pre_hashed_password() -> str:
    """Pre-compute the hashed password once for all tests to avoid repeated bcrypt operations."""
    return _PASSWORD_HASH.hash(DEFAULT_PASSWORD)


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

        app.dependency_overrides[get_session] = override_get_session
        v1_app.dependency_overrides[get_session] = override_get_session
        v2_app.dependency_overrides[get_session] = override_get_session

        yield app

        # Clean up
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{settings.postgres_db_schema}"'))

        # Clear any application dependencies
        app.dependency_overrides.clear()
        v1_app.dependency_overrides.clear()
        v2_app.dependency_overrides.clear()
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
async def user(db_session: AsyncSession, faker: Faker, pre_hashed_password: str) -> User:
    """Create a test user."""
    user_data = UserCreate(
        email=faker.safe_email(),
        username=faker.user_name(),
        hashed_password=pre_hashed_password,
        first_name=faker.first_name(),
        last_name=faker.last_name(),
    )
    user_db = await repos.UserRepo(db_session).create_one(user_data)
    return user_db


@pytest.fixture
async def other_user(
    db_session: AsyncSession,
    faker: Faker,
    pre_hashed_password: str,
) -> User:
    """Create another test user."""
    user_data = UserCreate(
        email=faker.safe_email(),
        username=faker.user_name(),
        hashed_password=pre_hashed_password,
        first_name=faker.first_name(),
        last_name=faker.last_name(),
    )
    user_db = await repos.UserRepo(db_session).create_one(user_data)
    return user_db


@pytest.fixture
async def default_password() -> str:
    return DEFAULT_PASSWORD


@pytest.fixture
async def token(user: User) -> Token:
    """Create a test token."""
    access_token_data = AuthService.create_access_token(subject=str(user.id))
    return Token(
        access_token=access_token_data["token"],
        token_type="Bearer",
    )
