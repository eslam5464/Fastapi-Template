"""Fixtures for the API tests."""

import time

import pytest


class FakeTokenBlacklist:
    """In-memory stand-in for the Redis-backed token blacklist.

    Same async interface as app.services.cache.token_blacklist.TokenBlacklist,
    so the API tests check token revocation without a Redis server.
    """

    def __init__(self) -> None:
        self.revoked: dict[str, int] = {}
        self.user_revocations: dict[str, int] = {}

    async def revoke_token(self, jti: str, ttl_seconds: int) -> bool:
        self.revoked[jti] = ttl_seconds
        return True

    async def is_revoked(self, jti: str) -> bool:
        return jti in self.revoked

    async def revoke_all_user_tokens(self, user_id: str, ttl_seconds: int) -> bool:
        self.user_revocations[user_id] = int(time.time())
        return True

    async def get_user_revocation_time(self, user_id: str) -> int | None:
        return self.user_revocations.get(user_id)


@pytest.fixture(autouse=True)
def fake_token_blacklist(monkeypatch: pytest.MonkeyPatch) -> FakeTokenBlacklist:
    """Replace the token blacklist used by the auth service and the logout endpoint.

    Tests that need specific blacklist answers still patch it themselves.
    """
    fake = FakeTokenBlacklist()
    monkeypatch.setattr("app.services.auth_service.token_blacklist", fake)
    monkeypatch.setattr("app.api.v1.endpoints.auth.token_blacklist", fake)
    return fake
