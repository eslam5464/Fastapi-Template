from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.config import Environment
from app.services.cache.base import BaseRedisClient, get_redis_pool


class TestGetRedisPool:
    """Test get_redis_pool function."""

    def test_get_redis_pool_creates_new_pool(self, mock_redis_pool: Mock):
        """Test creating new Redis pool."""
        # Reset global pool
        import app.services.cache.base as base_module

        base_module._redis_pool = None

        with patch("app.services.cache.base.ConnectionPool.from_url", return_value=mock_redis_pool):
            pool = get_redis_pool()

            assert pool == mock_redis_pool

    def test_get_redis_pool_returns_existing_pool(self, mock_redis_pool: Mock):
        """Test returning existing Redis pool."""
        import app.services.cache.base as base_module

        base_module._redis_pool = mock_redis_pool

        pool = get_redis_pool()

        assert pool == mock_redis_pool


class TestBaseRedisClient:
    """Test BaseRedisClient class."""

    def test_init_in_non_local_environment(self, mock_redis_pool: Mock):
        """Test initialization in non-local environment."""
        with patch("app.services.cache.base.settings.current_environment", Environment.DEV):
            with patch("app.services.cache.base.get_redis_pool", return_value=mock_redis_pool):
                with patch("app.services.cache.base.Redis") as mock_redis:
                    client = BaseRedisClient()

                    assert client.redis_client is not None

    def test_init_in_local_environment(self):
        """Test initialization in local environment."""
        with patch("app.services.cache.base.settings.current_environment", Environment.LOCAL):
            client = BaseRedisClient()

            # Should not have redis_client attribute set
            assert not hasattr(client, "redis_client") or client.redis_client is None

    def test_initialize_redis_success(self, mock_redis_pool: Mock):
        """Test successful Redis initialization."""
        with patch("app.services.cache.base.settings.current_environment", Environment.DEV):
            with patch("app.services.cache.base.get_redis_pool", return_value=mock_redis_pool):
                with patch("app.services.cache.base.Redis") as mock_redis_class:
                    mock_redis_instance = Mock()
                    mock_redis_class.return_value = mock_redis_instance

                    client = BaseRedisClient()

                    assert client.redis_client == mock_redis_instance

    def test_initialize_redis_failure(self):
        """Test Redis initialization failure."""
        with patch("app.services.cache.base.settings.current_environment", Environment.DEV):
            with patch(
                "app.services.cache.base.get_redis_pool", side_effect=Exception("Connection failed")
            ):
                with pytest.raises(Exception) as exc_info:
                    BaseRedisClient()

                assert "Connection failed" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_health_check_success(self, mock_redis_client: AsyncMock):
        """Test successful health check."""
        with patch("app.services.cache.base.settings.current_environment", Environment.DEV):
            client = BaseRedisClient.__new__(BaseRedisClient)
            client.redis_client = mock_redis_client
            mock_redis_client.ping = AsyncMock(return_value=True)

            result = await client.health_check()

            assert result is True
            mock_redis_client.ping.assert_called_once()

    @pytest.mark.anyio
    async def test_health_check_failure(self, mock_redis_client: AsyncMock):
        """Test failed health check."""
        with patch("app.services.cache.base.settings.current_environment", Environment.DEV):
            client = BaseRedisClient.__new__(BaseRedisClient)
            client.redis_client = mock_redis_client
            mock_redis_client.ping = AsyncMock(side_effect=Exception("Connection lost"))

            result = await client.health_check()

            assert result is False

    @pytest.mark.anyio
    async def test_close_success(self, mock_redis_client: AsyncMock):
        """Test successful close."""
        client = BaseRedisClient.__new__(BaseRedisClient)
        client.redis_client = mock_redis_client
        mock_redis_client.close = AsyncMock()

        await client.close()

        mock_redis_client.close.assert_called_once()

    @pytest.mark.anyio
    async def test_close_with_error(self, mock_redis_client: AsyncMock):
        """Test close with error."""
        client = BaseRedisClient.__new__(BaseRedisClient)
        client.redis_client = mock_redis_client
        mock_redis_client.close = AsyncMock(side_effect=Exception("Close failed"))

        # Should not raise exception
        await client.close()
