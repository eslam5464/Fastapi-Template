import hashlib
import time
from typing import TypedDict

from loguru import logger

from app.core.config import Environment, settings
from app.core.exceptions.rate_limiter import (
    RateLimitConfigurationError,
)
from app.services.cache import BaseRedisClient


class RateLimitInfo(TypedDict):
    """Rate limit information returned by check operations"""

    limit: int
    remaining: int
    reset_time: int
    window: int


class RateLimiter(BaseRedisClient):
    """
    Redis-based rate limiter using sliding window algorithm.

    Inherits Redis connection handling from BaseRedisClient and provides
    rate limiting operations using Redis sorted sets for accurate sliding window tracking.

    The sliding window algorithm:
    1. Stores timestamps of requests in a sorted set (ZSET)
    2. Removes requests outside the current time window
    3. Counts remaining requests in the window
    4. Allows or denies based on the limit

    Example:
        ```python
        # Check rate limit
        is_allowed, info = await rate_limiter.check_rate_limit(
            key="ratelimit:auth:192.168.1.1",
            limit=10,
            window=60
        )

        if not is_allowed:
            # Limit exceeded
            raise TooManyRequestsException(headers=...)
        ```
    """

    async def check_rate_limit(
        self, key: str, limit: int, window: int = 60
    ) -> tuple[bool, RateLimitInfo]:
        """
        Check if rate limit is exceeded for a given key.

        Args:
            key: Redis key for rate limiting (e.g., "ratelimit:auth:192.168.1.1")
            limit: Maximum number of requests allowed in the time window
            window: Time window in seconds (default: 60)

        Returns:
            tuple[bool, RateLimitInfo]: (is_allowed, rate_limit_info)
                - is_allowed: True if request is allowed, False if limit exceeded
                - rate_limit_info: Dictionary with limit details

        Raises:
            RateLimitConfigurationError: If limit or window is invalid

        Note:
            This method is safe to call even if Redis is unavailable.
            In LOCAL environment, always returns (True, info) without checking Redis.
        """
        # Validate configuration
        if limit <= 0:
            raise RateLimitConfigurationError(f"Rate limit must be positive, got {limit}")
        if window <= 0:
            raise RateLimitConfigurationError(f"Rate limit window must be positive, got {window}")

        # Skip rate limiting in LOCAL environment
        if settings.current_environment == Environment.LOCAL:
            return True, RateLimitInfo(
                limit=limit, remaining=limit, reset_time=int(time.time()) + window, window=window
            )

        # Check if Redis client is available
        if not self.redis_client:
            logger.warning(
                f"Redis client not initialized in RateLimiter, allowing request for key {key}"
            )
            return True, RateLimitInfo(
                limit=limit, remaining=limit, reset_time=int(time.time()) + window, window=window
            )

        try:
            now = int(time.time() * 1000000)  # Current time in microseconds
            window_start = now - (window * 1000000)  # Window start time in microseconds

            # Create pipeline for atomic operations
            pipe = self.redis_client.pipeline()

            # 1. Remove requests older than the window
            pipe.zremrangebyscore(key, 0, window_start)

            # 2. Add current request with unique timestamp-based member
            # Format: "{timestamp}:{hash}" to ensure uniqueness
            member = (
                f"{now}:{hashlib.md5(str(now).encode(), usedforsecurity=False).hexdigest()[:8]}"
            )
            pipe.zadd(key, {member: now})

            # 3. Count requests in current window (AFTER adding current request)
            pipe.zcard(key)

            # 4. Set expiration on key to auto-cleanup
            pipe.expire(key, window)

            # Execute pipeline
            results = await pipe.execute()
            request_count = results[2]  # ZCARD result (index 2 now, after ZADD)

            # Calculate rate limit info
            # request_count already includes the current request
            remaining = max(0, limit - request_count)
            reset_time = now + window
            is_allowed = request_count <= limit  # Changed from < to <=

            rate_limit_info = RateLimitInfo(
                limit=limit, remaining=remaining, reset_time=reset_time, window=window
            )

            return is_allowed, rate_limit_info

        except Exception as e:
            logger.warning(f"Rate limit check failed for key {key}: {e}. Allowing request.")
            # On error, allow request (fail open)
            return True, RateLimitInfo(
                limit=limit,
                remaining=limit,
                reset_time=int(time.time()) + window,
                window=window,
            )

    async def get_limit_info(self, key: str, limit: int, window: int = 60) -> RateLimitInfo:
        """
        Get current rate limit information without modifying counters.

        Args:
            key: Redis key for rate limiting
            limit: Maximum number of requests allowed
            window: Time window in seconds (default: 60)

        Returns:
            RateLimitInfo: Current rate limit status

        Note:
            This method only reads the current state, it does NOT increment counters.
            Use check_rate_limit() for actual rate limiting with counter increment.
        """
        if settings.current_environment == Environment.LOCAL or not self.redis_client:
            return RateLimitInfo(
                limit=limit,
                remaining=limit,
                reset_time=int(time.time()) + window,
                window=window,
            )

        try:
            now = int(time.time())
            window_start = now - window

            # Count requests in current window without modifying
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)  # Clean old entries
            pipe.zcard(key)
            results = await pipe.execute()

            request_count = results[1]
            remaining = max(0, limit - request_count)
            reset_time = now + window

            return RateLimitInfo(
                limit=limit, remaining=remaining, reset_time=reset_time, window=window
            )

        except Exception as e:
            logger.warning(f"Failed to get limit info for key {key}: {e}")
            return RateLimitInfo(
                limit=limit, remaining=limit, reset_time=int(time.time()) + window, window=window
            )

    async def reset_limit(self, key: str) -> bool:
        """
        Reset rate limit for a specific key.

        Args:
            key: Redis key to reset

        Returns:
            bool: True if key was deleted, False otherwise

        Note:
            This is useful for testing or manual intervention (e.g., unblocking a user).
        """
        if settings.current_environment == Environment.LOCAL or not self.redis_client:
            logger.debug(f"Skipping rate limit reset for key {key} (LOCAL environment or no Redis)")
            return True

        try:
            deleted = await self.redis_client.delete(key)
            if deleted:
                logger.info(f"Rate limit reset for key {key}")
            return deleted > 0
        except Exception as e:
            logger.warning(f"Failed to reset rate limit for key {key}: {e}")
            return False


rate_limiter = RateLimiter()
