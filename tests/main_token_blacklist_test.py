from unittest.mock import AsyncMock, patch

import pytest

import app.main as main_module
from app.core.config import Environment
from tests.utils import mock_lifespan_steps


@pytest.mark.anyio
class TestTokenBlacklistStartupCheck:
    """app.main._check_token_blacklist and its place in the lifespan."""

    async def test_skipped_in_local(self):
        with patch("app.main.token_blacklist.health_check", new_callable=AsyncMock) as check:
            with patch("app.main.settings.current_environment", Environment.LOCAL):
                await main_module._check_token_blacklist()

        check.assert_not_awaited()

    async def test_healthy_outside_local(self):
        with patch("app.main.token_blacklist.health_check", new_callable=AsyncMock, return_value=True) as check:
            with patch("app.main.settings.current_environment", Environment.DEV):
                with patch("app.main.logger") as logger:
                    await main_module._check_token_blacklist()

        check.assert_awaited_once()
        logger.success.assert_called_once()

    async def test_unhealthy_only_warns(self):
        with patch("app.main.token_blacklist.health_check", new_callable=AsyncMock, return_value=False):
            with patch("app.main.settings.current_environment", Environment.PRD):
                with patch("app.main.logger") as logger:
                    await main_module._check_token_blacklist()

        logger.warning.assert_called_once()

    async def test_check_dependencies_runs_blacklist_check(self, monkeypatch):
        mocks = mock_lifespan_steps(monkeypatch, main_module)

        await main_module._check_dependencies()

        mocks["_check_token_blacklist"].assert_awaited_once()


@pytest.mark.anyio
class TestTokenBlacklistShutdown:
    """app.main._close_token_blacklist and its place in the lifespan."""

    async def test_close(self):
        with patch("app.main.token_blacklist.close", new_callable=AsyncMock) as close:
            await main_module._close_token_blacklist()

        close.assert_awaited_once()

    async def test_shutdown_dependencies_closes_blacklist(self, monkeypatch):
        mocks = mock_lifespan_steps(monkeypatch, main_module)

        await main_module._shutdown_dependencies()

        mocks["_close_token_blacklist"].assert_awaited_once()
