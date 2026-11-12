import hashlib
import time

from loguru import logger
from redis.asyncio import Redis

from app.core.config import settings
from app.core.types import RateLimitInfoDict
from app.services.cache import BaseRedisClient
from app.services.exceptions.rate_limiter import (
    RateLimitConfigurationError,
)


class RateLimitPrefix:
    """
    Centralized registry of all rate limit key prefixes.

    All rate limit keys follow the pattern: ratelimit:{category}:{identifier}
    where identifier is typically an IP address or user ID.

    Example:
        ```python
        from app.services.cache.rate_limiter import RateLimitPrefix

        # Use in rate limiting
        key = f"{RateLimitPrefix.AUTH}{ip_address}"
        # Result: "ratelimit:auth:192.168.1.1"
        ```
    """

    # Authentication endpoints (login, signup, password reset)
    AUTH = "ratelimit:auth:"

    # Authenticated user endpoints (profile, settings, user data)
    USER = "ratelimit:user:"

    # General API endpoints (moderate limits)
    API = "ratelimit:api:"

    # Public endpoints (lenient limits for read-only operations)
    PUBLIC = "ratelimit:public:"

    # Custom endpoint-specific prefixes (add as needed)
    EXPORT = "ratelimit:export:"  # File export operations
    UPLOAD = "ratelimit:upload:"  # File upload operations
    SEARCH = "ratelimit:search:"  # Search queries
    ADMIN = "ratelimit:admin:"  # Admin operations

    @classmethod
    def all_prefixes(cls) -> set[str]:
        """
        Get all registered prefixes for validation.

        Returns:
            set[str]: Set of all registered rate limit prefixes

        Example:
            ```python
            prefixes = RateLimitPrefix.all_prefixes()
            # {'ratelimit:auth:', 'ratelimit:user:', ...}
            ```
        """
        return {
            value for key, value in cls.__dict__.items() if isinstance(value, str) and value.startswith("ratelimit:")
        }

    @classmethod
    def validate_prefix(cls, prefix: str) -> None:
        """
        Validate that a prefix doesn't conflict with existing ones.

        Args:
            prefix: The prefix to validate (should include "ratelimit:" and trailing ":")

        Raises:
            ValueError: If prefix already exists in the registry

        Example:
            ```python
            # This will raise ValueError if prefix already exists
            RateLimitPrefix.validate_prefix("ratelimit:custom:")
            ```
        """
        if prefix in cls.all_prefixes():
            raise ValueError(
                f"Rate limit prefix '{prefix}' is already registered. Existing prefixes: {cls.all_prefixes()}"
            )


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

    async def check_rate_limit(self, key: str, limit: int, window: int = 60) -> tuple[bool, RateLimitInfoDict]:
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
        """
        # Validate configuration
        if limit <= 0:
            raise RateLimitConfigurationError(f"Rate limit must be positive, got {limit}")
        if window <= 0:
            raise RateLimitConfigurationError(f"Rate limit window must be positive, got {window}")

        # Fail-open default: used both when rate limiting is disabled and when
        # Redis is unavailable or the check fails (see BaseRedisClient._safe_call).
        allow_default = (
            True,
            RateLimitInfoDict(limit=limit, remaining=limit, reset_time=int(time.time()) + window, window=window),
        )

        # Skip rate limiting if disabled
        if not settings.rate_limit_enabled:
            return allow_default

        async def _check(client: Redis) -> tuple[bool, RateLimitInfoDict]:
            now = int(time.time() * 1000000)  # Current time in microseconds
            window_start = now - (window * 1000000)  # Window start time in microseconds

            # Create pipeline for atomic operations
            pipe = client.pipeline()

            # 1. Remove requests older than the window
            pipe.zremrangebyscore(key, 0, window_start)

            # 2. Add current request with unique timestamp-based member
            # Format: "{timestamp}:{hash}" to ensure uniqueness
            member = f"{now}:{hashlib.md5(str(now).encode(), usedforsecurity=False).hexdigest()[:8]}"
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

            return is_allowed, RateLimitInfoDict(limit=limit, remaining=remaining, reset_time=reset_time, window=window)

        # Fail-open on Redis unavailability or error (see BaseRedisClient._safe_call).
        return await self._safe_call(_check, default=allow_default, context=f"Rate limit check for key {key}")

    async def get_limit_info(self, key: str, limit: int, window: int = 60) -> RateLimitInfoDict:
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
        default_info = RateLimitInfoDict(
            limit=limit, remaining=limit, reset_time=int(time.time()) + window, window=window
        )

        if not settings.rate_limit_enabled:
            return default_info

        async def _get_info(client: Redis) -> RateLimitInfoDict:
            now = int(time.time())
            window_start = now - window

            # Count requests in current window without modifying
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)  # Clean old entries
            pipe.zcard(key)
            results = await pipe.execute()

            request_count = results[1]
            remaining = max(0, limit - request_count)

            return RateLimitInfoDict(limit=limit, remaining=remaining, reset_time=now + window, window=window)

        return await self._safe_call(_get_info, default=default_info, context=f"Rate limit info for key {key}")

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
        # Nothing to reset if rate limiting is off or Redis isn't reachable — that's not
        # a failure, so it's handled here rather than folded into the shared fail-safe
        # shell below (which defaults to False, since an actual delete error is unknown state).
        if not settings.rate_limit_enabled:
            logger.debug(f"Skipping rate limit reset for key {key} (rate limiting disabled)")
            return True
        if not self.redis_client:
            logger.debug(f"Skipping rate limit reset for key {key} (Redis unavailable)")
            return True

        async def _reset(client: Redis) -> bool:
            deleted = await client.delete(key)
            if deleted:
                logger.info(f"Rate limit reset for key {key}")
            return bool(deleted > 0)

        return await self._safe_call(_reset, default=False, context=f"Rate limit reset for key {key}")


rate_limiter = RateLimiter()
