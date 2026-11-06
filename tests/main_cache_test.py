from unittest.mock import AsyncMock, patch

import pytest

import app.main as main_module
from tests.utils import mock_lifespan_steps


@pytest.mark.anyio
class TestCacheStartupCheck:
    """app.main._check_cache_manager and its place in the lifespan."""

    async def test_healthy(self):
        with patch("app.main.cache_manager.health_check", new_callable=AsyncMock, return_value=True) as check:
            with patch("app.main.settings.cache_enabled", True):
                await main_module._check_cache_manager()

        check.assert_awaited_once()

    async def test_unhealthy_and_enabled_fails_startup(self):
        with patch("app.main.cache_manager.health_check", new_callable=AsyncMock, return_value=False):
            with patch("app.main.settings.cache_enabled", True):
                with pytest.raises(RuntimeError, match="CacheManager is not healthy"):
                    await main_module._check_cache_manager()

    async def test_unhealthy_and_disabled_continues(self):
        with patch("app.main.cache_manager.health_check", new_callable=AsyncMock, return_value=False) as check:
            with patch("app.main.settings.cache_enabled", False):
                await main_module._check_cache_manager()

        check.assert_awaited_once()

    async def test_check_dependencies_runs_cache_check(self, monkeypatch):
        mocks = mock_lifespan_steps(monkeypatch, main_module)

        await main_module._check_dependencies()

        mocks["_check_cache_manager"].assert_awaited_once()

    async def test_cache_failure_stops_check_dependencies(self, monkeypatch):
        mocks = mock_lifespan_steps(monkeypatch, main_module)
        mocks["_check_cache_manager"].side_effect = RuntimeError("CacheManager is not healthy.")

        with pytest.raises(RuntimeError, match="CacheManager is not healthy"):
            await main_module._check_dependencies()


@pytest.mark.anyio
class TestCacheShutdown:
    """app.main._close_cache_manager and its place in the lifespan."""

    async def test_close(self):
        with patch("app.main.cache_manager.close", new_callable=AsyncMock) as close:
            await main_module._close_cache_manager()

        close.assert_awaited_once()

    async def test_shutdown_dependencies_closes_cache(self, monkeypatch):
        mocks = mock_lifespan_steps(monkeypatch, main_module)

        await main_module._shutdown_dependencies()

        mocks["_close_cache_manager"].assert_awaited_once()

    async def test_close_errors_propagate(self, monkeypatch):
        mocks = mock_lifespan_steps(monkeypatch, main_module)
        mocks["_close_cache_manager"].side_effect = Exception("Cache close failed")

        with pytest.raises(Exception, match="Cache close failed"):
            await main_module._shutdown_dependencies()
