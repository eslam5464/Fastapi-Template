import pickle
from unittest.mock import AsyncMock

import pytest

from app.services.cache.manager import CacheManager


class TestCacheManager:
    """Test CacheManager class."""

    @pytest.mark.anyio
    async def test_get_success(self, mock_redis_client: AsyncMock):
        """Test successful get operation."""
        cached_value = {"test": "data"}
        mock_redis_client.get = AsyncMock(return_value=pickle.dumps(cached_value))

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client  # type: ignore

        result = await cache_manager.get("test_key")

        assert result == cached_value
        mock_redis_client.get.assert_called_once_with("test_key")

    @pytest.mark.anyio
    async def test_get_not_found(self, mock_redis_client: AsyncMock):
        """Test get when key not found."""
        mock_redis_client.get = AsyncMock(return_value=None)

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.get("missing_key")

        assert result is None

    @pytest.mark.anyio
    async def test_get_no_redis_client(self):
        """Test get when Redis client not initialized."""
        cache_manager = CacheManager()
        cache_manager.redis_client = None  # type: ignore

        result = await cache_manager.get("test_key")

        assert result is None

    @pytest.mark.anyio
    async def test_get_with_exception(self, mock_redis_client: AsyncMock):
        """Test get with exception."""
        mock_redis_client.get = AsyncMock(side_effect=Exception("Redis error"))

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.get("test_key")

        assert result is None

    @pytest.mark.anyio
    async def test_set_success(self, mock_redis_client: AsyncMock):
        """Test successful set operation."""
        mock_redis_client.set = AsyncMock(return_value=True)

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.set("test_key", {"data": "value"}, expire=60)

        assert result is True
        mock_redis_client.set.assert_called_once()

    @pytest.mark.anyio
    async def test_set_with_default_expire(self, mock_redis_client: AsyncMock):
        """Test set with default expiration."""
        mock_redis_client.set = AsyncMock(return_value=True)

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.set("test_key", "value")

        assert result is True

    @pytest.mark.anyio
    async def test_set_no_redis_client(self):
        """Test set when Redis client not initialized."""
        cache_manager = CacheManager()
        cache_manager.redis_client = None

        result = await cache_manager.set("test_key", "value")

        assert result is False

    @pytest.mark.anyio
    async def test_set_with_exception(self, mock_redis_client: AsyncMock):
        """Test set with exception."""
        mock_redis_client.set = AsyncMock(side_effect=Exception("Redis error"))

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.set("test_key", "value")

        assert result is False

    @pytest.mark.anyio
    async def test_delete_success(self, mock_redis_client: AsyncMock):
        """Test successful delete operation."""
        mock_redis_client.delete = AsyncMock(return_value=1)

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.delete("test_key")

        assert result is True
        mock_redis_client.delete.assert_called_once_with("test_key")

    @pytest.mark.anyio
    async def test_delete_key_not_exists(self, mock_redis_client: AsyncMock):
        """Test delete when key doesn't exist."""
        mock_redis_client.delete = AsyncMock(return_value=0)

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.delete("missing_key")

        assert result is False

    @pytest.mark.anyio
    async def test_delete_no_redis_client(self):
        """Test delete when Redis client not initialized."""
        cache_manager = CacheManager()
        cache_manager.redis_client = None  # type: ignore

        result = await cache_manager.delete("test_key")

        assert result is False

    @pytest.mark.anyio
    async def test_delete_with_exception(self, mock_redis_client: AsyncMock):
        """Test delete with exception."""
        mock_redis_client.delete = AsyncMock(side_effect=Exception("Redis error"))

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.delete("test_key")

        assert result is False

    @pytest.mark.anyio
    async def test_delete_pattern_success(self, mock_redis_client: AsyncMock):
        """Test successful delete_pattern operation."""
        mock_redis_client.keys = AsyncMock(return_value=[b"key1", b"key2"])
        mock_redis_client.delete = AsyncMock(return_value=2)

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.delete_pattern("test_*")

        assert result == 2
        mock_redis_client.keys.assert_called_once_with("test_*")
        mock_redis_client.delete.assert_called_once()

    @pytest.mark.anyio
    async def test_delete_pattern_no_matches(self, mock_redis_client: AsyncMock):
        """Test delete_pattern with no matching keys."""
        mock_redis_client.keys = AsyncMock(return_value=[])

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.delete_pattern("test_*")

        assert result == 0

    @pytest.mark.anyio
    async def test_delete_pattern_no_redis_client(self):
        """Test delete_pattern when Redis client not initialized."""
        cache_manager = CacheManager()
        cache_manager.redis_client = None  # type: ignore

        result = await cache_manager.delete_pattern("test_*")

        assert result == 0

    @pytest.mark.anyio
    async def test_delete_pattern_with_exception(self, mock_redis_client: AsyncMock):
        """Test delete_pattern with exception."""
        mock_redis_client.keys = AsyncMock(side_effect=Exception("Redis error"))

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.delete_pattern("test_*")

        assert result == 0

    @pytest.mark.anyio
    async def test_exists_true(self, mock_redis_client: AsyncMock):
        """Test exists when key exists."""
        mock_redis_client.exists = AsyncMock(return_value=1)

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.exists("test_key")

        assert result is True
        mock_redis_client.exists.assert_called_once_with("test_key")

    @pytest.mark.anyio
    async def test_exists_false(self, mock_redis_client: AsyncMock):
        """Test exists when key doesn't exist."""
        mock_redis_client.exists = AsyncMock(return_value=0)

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.exists("missing_key")

        assert result is False

    @pytest.mark.anyio
    async def test_exists_no_redis_client(self):
        """Test exists when Redis client not initialized."""
        cache_manager = CacheManager()
        cache_manager.redis_client = None  # type: ignore

        result = await cache_manager.exists("test_key")

        assert result is False

    @pytest.mark.anyio
    async def test_exists_with_exception(self, mock_redis_client: AsyncMock):
        """Test exists with exception."""
        mock_redis_client.exists = AsyncMock(side_effect=Exception("Redis error"))

        cache_manager = CacheManager()
        cache_manager.redis_client = mock_redis_client

        result = await cache_manager.exists("test_key")

        assert result is False
