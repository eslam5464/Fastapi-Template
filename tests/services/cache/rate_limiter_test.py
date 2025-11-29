from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.exceptions.rate_limiter import RateLimitConfigurationError
from app.services.cache.rate_limiter import RateLimiter


class TestRateLimiterConfiguration:
    """Test RateLimiter configuration and validation."""

    @pytest.mark.anyio
    async def test_check_rate_limit_invalid_limit(self, mock_redis_client: AsyncMock):
        """Test check_rate_limit with invalid limit."""
        rate_limiter = RateLimiter()
        rate_limiter.redis_client = mock_redis_client

        with pytest.raises(RateLimitConfigurationError) as exc_info:
            await rate_limiter.check_rate_limit("test_key", limit=0, window=60)

        assert "must be positive" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_check_rate_limit_negative_limit(self, mock_redis_client: AsyncMock):
        """Test check_rate_limit with negative limit."""
        rate_limiter = RateLimiter()
        rate_limiter.redis_client = mock_redis_client

        with pytest.raises(RateLimitConfigurationError):
            await rate_limiter.check_rate_limit("test_key", limit=-5, window=60)

    @pytest.mark.anyio
    async def test_check_rate_limit_invalid_window(self, mock_redis_client: AsyncMock):
        """Test check_rate_limit with invalid window."""
        rate_limiter = RateLimiter()
        rate_limiter.redis_client = mock_redis_client

        with pytest.raises(RateLimitConfigurationError) as exc_info:
            await rate_limiter.check_rate_limit("test_key", limit=10, window=0)

        assert "window must be positive" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_check_rate_limit_negative_window(self, mock_redis_client: AsyncMock):
        """Test check_rate_limit with negative window."""
        rate_limiter = RateLimiter()
        rate_limiter.redis_client = mock_redis_client

        with pytest.raises(RateLimitConfigurationError):
            await rate_limiter.check_rate_limit("test_key", limit=10, window=-1)


class TestRateLimiterDisabled:
    """Test RateLimiter when disabled."""

    @pytest.mark.anyio
    async def test_check_rate_limit_when_disabled(self):
        """Test check_rate_limit when rate limiting is disabled."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", False):
            rate_limiter = RateLimiter()

            is_allowed, info = await rate_limiter.check_rate_limit("test_key", limit=10, window=60)

            assert is_allowed is True
            assert info["limit"] == 10
            assert info["remaining"] == 10

    @pytest.mark.anyio
    async def test_get_limit_info_when_disabled(self):
        """Test get_limit_info when rate limiting is disabled."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", False):
            rate_limiter = RateLimiter()

            info = await rate_limiter.get_limit_info("test_key", limit=10, window=60)

            assert info["limit"] == 10
            assert info["remaining"] == 10


class TestRateLimiterNoRedis:
    """Test RateLimiter when Redis is unavailable."""

    @pytest.mark.anyio
    async def test_check_rate_limit_no_redis_client(self):
        """Test check_rate_limit when Redis client not initialized."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            rate_limiter = RateLimiter()
            rate_limiter.redis_client = None

            is_allowed, info = await rate_limiter.check_rate_limit("test_key", limit=10, window=60)

            assert is_allowed is True
            assert info["limit"] == 10

    @pytest.mark.anyio
    async def test_get_limit_info_no_redis_client(self):
        """Test get_limit_info when Redis client not initialized."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            rate_limiter = RateLimiter()
            rate_limiter.redis_client = None

            info = await rate_limiter.get_limit_info("test_key", limit=10, window=60)

            assert info["limit"] == 10
            assert info["remaining"] == 10


class TestRateLimiterOperations:
    """Test RateLimiter rate limiting operations."""

    @pytest.mark.anyio
    async def test_check_rate_limit_allowed(self, mock_redis_client: AsyncMock):
        """Test check_rate_limit when request is allowed."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            # Mock pipeline operations
            mock_pipeline = AsyncMock()
            mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
            mock_pipeline.zadd = Mock(return_value=mock_pipeline)
            mock_pipeline.zcard = Mock(return_value=mock_pipeline)
            mock_pipeline.expire = Mock(return_value=mock_pipeline)
            mock_pipeline.execute = AsyncMock(return_value=[0, 1, 3, True])  # 3 requests in window

            mock_redis_client.pipeline = Mock(return_value=mock_pipeline)

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            is_allowed, info = await rate_limiter.check_rate_limit("test_key", limit=10, window=60)

            assert is_allowed is True
            assert info["limit"] == 10
            assert info["remaining"] == 7
            assert info["window"] == 60

    @pytest.mark.anyio
    async def test_check_rate_limit_exceeded(self, mock_redis_client: AsyncMock):
        """Test check_rate_limit when limit is exceeded."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            mock_pipeline = AsyncMock()
            mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
            mock_pipeline.zadd = Mock(return_value=mock_pipeline)
            mock_pipeline.zcard = Mock(return_value=mock_pipeline)
            mock_pipeline.expire = Mock(return_value=mock_pipeline)
            mock_pipeline.execute = AsyncMock(
                return_value=[0, 1, 11, True]
            )  # 11 requests, limit is 10

            mock_redis_client.pipeline = Mock(return_value=mock_pipeline)

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            is_allowed, info = await rate_limiter.check_rate_limit("test_key", limit=10, window=60)

            assert is_allowed is False
            assert info["remaining"] == 0

    @pytest.mark.anyio
    async def test_check_rate_limit_at_boundary(self, mock_redis_client: AsyncMock):
        """Test check_rate_limit at exact limit boundary."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            mock_pipeline = AsyncMock()
            mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
            mock_pipeline.zadd = Mock(return_value=mock_pipeline)
            mock_pipeline.zcard = Mock(return_value=mock_pipeline)
            mock_pipeline.expire = Mock(return_value=mock_pipeline)
            mock_pipeline.execute = AsyncMock(return_value=[0, 1, 10, True])  # Exactly at limit

            mock_redis_client.pipeline = Mock(return_value=mock_pipeline)

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            is_allowed, info = await rate_limiter.check_rate_limit("test_key", limit=10, window=60)

            assert is_allowed is True
            assert info["remaining"] == 0

    @pytest.mark.anyio
    async def test_check_rate_limit_with_exception(self, mock_redis_client: AsyncMock):
        """Test check_rate_limit handles exceptions gracefully."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            mock_redis_client.pipeline = Mock(side_effect=Exception("Redis error"))

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            is_allowed, info = await rate_limiter.check_rate_limit("test_key", limit=10, window=60)

            # Should allow request on error (fail open)
            assert is_allowed is True
            assert info["limit"] == 10

    @pytest.mark.anyio
    async def test_get_limit_info_success(self, mock_redis_client: AsyncMock):
        """Test get_limit_info returns current state."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            mock_pipeline = AsyncMock()
            mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
            mock_pipeline.zcard = Mock(return_value=mock_pipeline)
            mock_pipeline.execute = AsyncMock(return_value=[0, 5])

            mock_redis_client.pipeline = Mock(return_value=mock_pipeline)

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            info = await rate_limiter.get_limit_info("test_key", limit=10, window=60)

            assert info["limit"] == 10
            assert info["remaining"] == 5

    @pytest.mark.anyio
    async def test_get_limit_info_with_exception(self, mock_redis_client: AsyncMock):
        """Test get_limit_info with exception."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            mock_redis_client.pipeline = Mock(side_effect=Exception("Redis error"))

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            info = await rate_limiter.get_limit_info("test_key", limit=10, window=60)

            assert info["limit"] == 10
            assert info["remaining"] == 10

    @pytest.mark.anyio
    async def test_reset_limit_success(self, mock_redis_client: AsyncMock):
        """Test successful reset_limit."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            mock_redis_client.delete = AsyncMock(return_value=1)

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            result = await rate_limiter.reset_limit("test_key")

            assert result is True
            mock_redis_client.delete.assert_called_once_with("test_key")

    @pytest.mark.anyio
    async def test_reset_limit_key_not_exists(self, mock_redis_client: AsyncMock):
        """Test reset_limit when key doesn't exist."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            mock_redis_client.delete = AsyncMock(return_value=0)

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            result = await rate_limiter.reset_limit("test_key")

            assert result is False

    @pytest.mark.anyio
    async def test_reset_limit_when_disabled(self):
        """Test reset_limit when rate limiting is disabled."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", False):
            rate_limiter = RateLimiter()

            result = await rate_limiter.reset_limit("test_key")

            assert result is True

    @pytest.mark.anyio
    async def test_reset_limit_no_redis_client(self):
        """Test reset_limit when Redis client not initialized."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            rate_limiter = RateLimiter()
            rate_limiter.redis_client = None

            result = await rate_limiter.reset_limit("test_key")

            assert result is True

    @pytest.mark.anyio
    async def test_reset_limit_with_exception(self, mock_redis_client: AsyncMock):
        """Test reset_limit with exception."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            mock_redis_client.delete = AsyncMock(side_effect=Exception("Redis error"))

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            result = await rate_limiter.reset_limit("test_key")

            assert result is False


class TestRateLimiterSlidingWindow:
    """Test RateLimiter sliding window algorithm."""

    @pytest.mark.anyio
    async def test_sliding_window_removes_old_requests(self, mock_redis_client: AsyncMock):
        """Test that sliding window removes old requests."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            mock_pipeline = AsyncMock()
            mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
            mock_pipeline.zadd = Mock(return_value=mock_pipeline)
            mock_pipeline.zcard = Mock(return_value=mock_pipeline)
            mock_pipeline.expire = Mock(return_value=mock_pipeline)
            mock_pipeline.execute = AsyncMock(return_value=[5, 1, 3, True])  # Removed 5 old entries

            mock_redis_client.pipeline = Mock(return_value=mock_pipeline)

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            is_allowed, info = await rate_limiter.check_rate_limit("test_key", limit=10, window=60)

            assert is_allowed is True
            # Verify zremrangebyscore was called (removes old entries)
            mock_pipeline.zremrangebyscore.assert_called_once()

    @pytest.mark.anyio
    async def test_sliding_window_adds_current_request(self, mock_redis_client: AsyncMock):
        """Test that sliding window adds current request."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            mock_pipeline = AsyncMock()
            mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
            mock_pipeline.zadd = Mock(return_value=mock_pipeline)
            mock_pipeline.zcard = Mock(return_value=mock_pipeline)
            mock_pipeline.expire = Mock(return_value=mock_pipeline)
            mock_pipeline.execute = AsyncMock(return_value=[0, 1, 5, True])

            mock_redis_client.pipeline = Mock(return_value=mock_pipeline)

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            await rate_limiter.check_rate_limit("test_key", limit=10, window=60)

            # Verify zadd was called (adds current request)
            mock_pipeline.zadd.assert_called_once()

    @pytest.mark.anyio
    async def test_sliding_window_sets_expiration(self, mock_redis_client: AsyncMock):
        """Test that sliding window sets key expiration."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            mock_pipeline = AsyncMock()
            mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
            mock_pipeline.zadd = Mock(return_value=mock_pipeline)
            mock_pipeline.zcard = Mock(return_value=mock_pipeline)
            mock_pipeline.expire = Mock(return_value=mock_pipeline)
            mock_pipeline.execute = AsyncMock(return_value=[0, 1, 5, True])

            mock_redis_client.pipeline = Mock(return_value=mock_pipeline)

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            await rate_limiter.check_rate_limit("test_key", limit=10, window=60)

            # Verify expire was called
            mock_pipeline.expire.assert_called_once()

    @pytest.mark.anyio
    async def test_sliding_window_custom_window(self, mock_redis_client: AsyncMock):
        """Test sliding window with custom window size."""
        with patch("app.services.cache.rate_limiter.settings.rate_limit_enabled", True):
            mock_pipeline = AsyncMock()
            mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
            mock_pipeline.zadd = Mock(return_value=mock_pipeline)
            mock_pipeline.zcard = Mock(return_value=mock_pipeline)
            mock_pipeline.expire = Mock(return_value=mock_pipeline)
            mock_pipeline.execute = AsyncMock(return_value=[0, 1, 5, True])

            mock_redis_client.pipeline = Mock(return_value=mock_pipeline)

            rate_limiter = RateLimiter()
            rate_limiter.redis_client = mock_redis_client

            is_allowed, info = await rate_limiter.check_rate_limit(
                "test_key", limit=100, window=120
            )

            assert is_allowed is True
            assert info["window"] == 120
            assert info["limit"] == 100
