import pickle
from typing import Any, Optional

from loguru import logger

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
        if not self.redis_client:
            logger.warning("Redis client not initialized in CacheManager")
            return None

        try:
            data = await self.redis_client.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None

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
        if not self.redis_client:
            logger.warning("Redis client not initialized in CacheManager")
            return False

        try:
            serialized = pickle.dumps(value)
            expire = expire or settings.cache_ttl_default
            return await self.redis_client.set(key, serialized, ex=expire)
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete cached data

        Args:
            key (str): Cache key

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        if not self.redis_client:
            logger.warning("Redis client not initialized in CacheManager")
            return False

        try:
            return await self.redis_client.delete(key) > 0
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete keys matching pattern

        Args:
            pattern (str): Pattern to match keys

        Returns:
            int: Number of keys deleted
        """
        if not self.redis_client:
            logger.warning("Redis client not initialized in CacheManager")
            return 0

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern failed for pattern {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        Check if key exists

        Args:
            key (str): Cache key

        Returns:
            bool: True if key exists, False otherwise
        """
        if not self.redis_client:
            logger.warning("Redis client not initialized in CacheManager")
            return False

        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists check failed for key {key}: {e}")
            return False


# Global cache manager instance
cache_manager = CacheManager()
