"""The rate limit dependencies are wired into the routers and the header middleware."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models import User

CHECK = "app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit"


def _info(limit: int, remaining: int) -> dict:
    return {"limit": limit, "remaining": remaining, "reset_time": 1764425820}


@pytest.mark.anyio
class TestRateLimitWiring:
    async def test_login_over_the_limit_gets_429(self, client: AsyncClient, user: User, default_password: str):
        with patch(CHECK, new_callable=AsyncMock, return_value=(False, _info(10, 0))) as check:
            response = await client.post(
                "/v1/auth/login",
                data={"username": user.username, "password": default_password},
            )

        assert response.status_code == 429, response.text
        assert response.headers["X-RateLimit-Limit"] == "10"
        assert response.headers["X-RateLimit-Remaining"] == "0"
        assert check.await_args.kwargs["key"].startswith("ratelimit:auth:")

    async def test_login_within_the_limit_gets_rate_limit_headers(
        self, client: AsyncClient, user: User, default_password: str
    ):
        with patch(CHECK, new_callable=AsyncMock, return_value=(True, _info(10, 9))):
            response = await client.post(
                "/v1/auth/login",
                data={"username": user.username, "password": default_password},
            )

        assert response.status_code == 200, response.text
        assert response.headers["X-RateLimit-Limit"] == "10"
        assert response.headers["X-RateLimit-Remaining"] == "9"

    async def test_users_me_over_the_limit_gets_429(self, client: AsyncClient, user: User, default_password: str):
        login = await client.post("/v1/auth/login", data={"username": user.username, "password": default_password})
        access_token = login.json()["access_token"]

        with patch(CHECK, new_callable=AsyncMock, return_value=(False, _info(60, 0))) as check:
            response = await client.get("/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})

        assert response.status_code == 429, response.text
        assert check.await_args.kwargs["key"].startswith("ratelimit:userip:users:me:get:")
