"""Fixtures for the tests of the authenticated v1 API: users and tokens."""

import pytest
from faker import Faker
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from app import repos
from app.models import User
from app.schemas import Token, UserCreate
from app.services.auth_service import AuthService

DEFAULT_PASSWORD = "P@ssword123"
_PASSWORD_HASH = PasswordHash.recommended()


@pytest.fixture(scope="session")
def pre_hashed_password() -> str:
    """Pre-compute the hashed password once for all tests to avoid repeated bcrypt operations."""
    return _PASSWORD_HASH.hash(DEFAULT_PASSWORD)


@pytest.fixture
async def user(db_session: AsyncSession, faker: Faker, pre_hashed_password: str) -> User:
    """Create a test user."""
    user_data = UserCreate(
        email=faker.unique.safe_email(),
        username=faker.unique.user_name(),
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
        email=faker.unique.safe_email(),
        username=faker.unique.user_name(),
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
