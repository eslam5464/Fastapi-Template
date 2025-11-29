from abc import ABC

from loguru import logger
from redis.asyncio import Redis

from app.core.config import Environment, settings


class BaseRedisClient(ABC):
    """
    Abstract base class for Redis clients with shared connection handling.

    Provides core Redis connection initialization, health checks, and availability checks
    that are inherited by all Redis-based services (CacheManager, SecurityCache, etc.).
    """

    def __init__(self):
        self.redis_client: Redis

        # Only initialize Redis in non-local environments
        if settings.current_environment != Environment.LOCAL:
            self._initialize_redis()

    def _initialize_redis(self):
        """Initialize Redis connection with retry and timeout settings"""
        try:
            self.redis_client = Redis.from_url(
                settings.redis_url.human_repr(),
                encoding="utf-8",
                decode_responses=False,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Redis for {self.__class__.__name__}: {e}")
            raise e

    async def health_check(self) -> bool:
        """
        Check Redis connection health by pinging the server.

        Returns:
            bool: True if Redis is healthy and responsive, False otherwise
        """
        try:
            await self.redis_client.ping()  # type: ignore
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed for {self.__class__.__name__}: {e}")
            return False

    async def close(self):
        """Close Redis connection gracefully"""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info(f"Redis connection closed for {self.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error closing Redis connection for {self.__class__.__name__}: {e}")
