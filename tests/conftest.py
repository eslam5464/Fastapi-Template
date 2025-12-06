import asyncio
from datetime import UTC, datetime, timedelta
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from faker import Faker
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import text

from app import repos
from app.core.auth import get_password_hash
from app.core.config import settings
from app.core.db import get_session
from app.main import app
from app.models import Base, User
from app.schemas import Token, UserCreate

DEFAULT_PASSWORD = "P@ssword123"


@pytest.fixture(scope="session")
def pre_hashed_password():
    """Pre-compute the hashed password once for all tests to avoid repeated bcrypt operations."""
    return get_password_hash(DEFAULT_PASSWORD)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")  # Change to function scope
async def test_app() -> AsyncGenerator[FastAPI, None]:
    """Create a FastAPI test application with an async database session."""
    # Override the database settings for testing
    test_engine = create_async_engine(settings.db_test_url.human_repr(), echo=False)

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

    yield app

    # Clean up
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text(f'DROP SCHEMA IF EXISTS "{settings.postgres_db_schema}"'))

    # Clear any application dependencies
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def faker() -> Faker:
    """Create a Faker instance for generating test data."""
    return Faker()


@pytest_asyncio.fixture
async def db_session(test_app: FastAPI) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for a test."""
    test_engine = create_async_engine(settings.db_test_url.human_repr())
    test_async_session = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async with test_async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
async def default_password() -> str:
    return DEFAULT_PASSWORD


@pytest_asyncio.fixture
async def token(user: User) -> Token:
    """Create a test token."""
    access_token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": datetime.now(UTC) + timedelta(seconds=settings.access_token_expire_seconds),
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return Token(
        access_token=access_token,
        token_type="Bearer",
    )
