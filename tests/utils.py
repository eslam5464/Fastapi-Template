from types import ModuleType
from unittest.mock import AsyncMock

import pytest
from faker import Faker

from tests.schemas import UserCredentials


def generate_user_credentials() -> UserCredentials:
    """
    Generate random user credentials (username and password)
    Returns:
        UserCredentials: Generated username and password
    """
    faker = Faker()
    username = faker.password(length=10, upper_case=True, lower_case=True, digits=True, special_chars=False)
    password = faker.password(length=12, special_chars=False, digits=True, upper_case=True, lower_case=True) + "@%&"
    email = faker.unique.safe_email()
    return UserCredentials(username=username, password=password, email=email)


def mock_lifespan_steps(monkeypatch: pytest.MonkeyPatch, main_module: ModuleType) -> dict[str, AsyncMock]:
    """
    Replace every per-service startup check (`_check_*`) and shutdown step
    (`_close_*`) of app.main with an AsyncMock.

    Tests for one service mock the others this way, so they do not depend on
    which other services the project includes.

    Returns:
        dict[str, AsyncMock]: The mocks by function name.
    """
    mocks: dict[str, AsyncMock] = {}
    for name in dir(main_module):
        if (name.startswith("_check_") and name != "_check_dependencies") or name.startswith("_close_"):
            mocks[name] = AsyncMock()
            monkeypatch.setattr(main_module, name, mocks[name])
    return mocks
