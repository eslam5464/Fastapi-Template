# Justification for the nosec markers below: see the comment on pickle.loads() further down.
import pickle  # nosec B403
from typing import Any, Optional

from redis.asyncio import Redis

from app.core.config import settings
from app.services.cache import BaseRedisClient


class CacheManager(BaseRedisClient):
    """
    Cache manager for general-purpose data caching with pickle serialization.

    Inherits Redis connection handling from BaseRedisClient and provides
    high-level caching operations for any Python object using pickle.
    """

    async def get(self, key: str) -> Optional[Any]:
        """
        Get cached data

        Args:
            key (str): Cache key

        Returns:
            Optional[Any]: Cached value or None if not found
        """

        async def _get(client: Redis) -> Optional[Any]:
            data = await client.get(key)
            # Accepted risk: only this service ever writes to these keys (via set()
            # below), and Redis is treated as trusted internal infra, not attacker-
            # reachable storage. Revisit if that trust boundary ever changes (e.g.
            # Redis shared with untrusted services) by switching to JSON.
            return pickle.loads(data) if data else None  # nosec B301

        return await self._safe_call(_get, default=None, context=f"Cache get for key {key}")

    async def set(self, key: str, value: Any, expire: int | None = None) -> bool:
        """
        Set cached data with expiration

        Args:
            key (str): Cache key
            value (Any): Value to cache
            expire (int | None): Expiration time in seconds. If None, uses default TTL.

        Returns:
            bool: True if set successfully, False otherwise
        """
        ttl = expire or settings.cache_ttl_default

        async def _set(client: Redis) -> bool:
            serialized = pickle.dumps(value)
            return bool(await client.set(key, serialized, ex=ttl))

        return await self._safe_call(_set, default=False, context=f"Cache set for key {key}")

    async def delete(self, key: str) -> bool:
        """
        Delete cached data

        Args:
            key (str): Cache key

        Returns:
            bool: True if deleted successfully, False otherwise
        """

        async def _delete(client: Redis) -> bool:
            return bool(await client.delete(key) > 0)

        return await self._safe_call(_delete, default=False, context=f"Cache delete for key {key}")

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete keys matching pattern

        Args:
            pattern (str): Pattern to match keys

        Returns:
            int: Number of keys deleted
        """

        async def _delete_pattern(client: Redis) -> int:
            keys = await client.keys(pattern)
            if keys:
                return int(await client.delete(*keys))
            return 0

        return await self._safe_call(
            _delete_pattern, default=0, context=f"Cache delete pattern {pattern}"
        )

    async def exists(self, key: str) -> bool:
        """
        Check if key exists

        Args:
            key (str): Cache key

        Returns:
            bool: True if key exists, False otherwise
        """

        async def _exists(client: Redis) -> bool:
            return bool(await client.exists(key) > 0)

        return await self._safe_call(
            _exists, default=False, context=f"Cache exists check for key {key}"
        )


# Global cache manager instance
cache_manager = CacheManager()
