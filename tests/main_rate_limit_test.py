from unittest.mock import AsyncMock, patch

import pytest

import app.main as main_module
from tests.utils import mock_lifespan_steps


@pytest.mark.anyio
class TestRateLimiterStartupCheck:
    """app.main._check_rate_limiter and its place in the lifespan."""

    async def test_healthy(self):
        with patch("app.main.rate_limiter.health_check", new_callable=AsyncMock, return_value=True) as check:
            with patch("app.main.settings.rate_limit_enabled", True):
                await main_module._check_rate_limiter()

        check.assert_awaited_once()

    async def test_unhealthy_and_enabled_fails_startup(self):
        with patch("app.main.rate_limiter.health_check", new_callable=AsyncMock, return_value=False):
            with patch("app.main.settings.rate_limit_enabled", True):
                with pytest.raises(RuntimeError, match="RateLimiter is not healthy"):
                    await main_module._check_rate_limiter()

    async def test_unhealthy_and_disabled_continues(self):
        with patch("app.main.rate_limiter.health_check", new_callable=AsyncMock, return_value=False) as check:
            with patch("app.main.settings.rate_limit_enabled", False):
                await main_module._check_rate_limiter()

        check.assert_awaited_once()

    async def test_check_dependencies_runs_rate_limiter_check(self, monkeypatch):
        mocks = mock_lifespan_steps(monkeypatch, main_module)

        await main_module._check_dependencies()

        mocks["_check_rate_limiter"].assert_awaited_once()


@pytest.mark.anyio
class TestRateLimiterShutdown:
    """app.main._close_rate_limiter and its place in the lifespan."""

    async def test_close(self):
        with patch("app.main.rate_limiter.close", new_callable=AsyncMock) as close:
            await main_module._close_rate_limiter()

        close.assert_awaited_once()

    async def test_shutdown_dependencies_closes_rate_limiter(self, monkeypatch):
        mocks = mock_lifespan_steps(monkeypatch, main_module)

        await main_module._shutdown_dependencies()

        mocks["_close_rate_limiter"].assert_awaited_once()


def test_rate_limit_header_middleware_registered():
    middleware_types = [m.cls.__name__ for m in main_module.app.user_middleware]

    assert "RateLimitHeaderMiddleware" in middleware_types
