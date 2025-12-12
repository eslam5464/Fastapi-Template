from abc import ABC

from loguru import logger
from redis.asyncio import ConnectionPool, Redis

from app.core.config import Environment, settings

# Global shared Redis connection pool
_redis_pool: ConnectionPool | None = None


def get_redis_pool() -> ConnectionPool:
    """
    Get or create the shared Redis connection pool.

    Returns:
        ConnectionPool: Shared Redis connection pool instance

    Note:
        This ensures all Redis clients share the same connection pool,
        improving resource efficiency and connection management.
    """
    global _redis_pool

    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            settings.redis_url.human_repr(),
            encoding="utf-8",
            decode_responses=False,
            max_connections=settings.redis_max_pool_connections,
            retry_on_timeout=True,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
            socket_timeout=settings.redis_socket_timeout,
        )
        logger.info(
            f"Redis connection pool created with max_connections={settings.redis_max_pool_connections}"
        )
    return _redis_pool


class BaseRedisClient(ABC):
    """
    Abstract base class for Redis clients with shared connection handling.

    Provides core Redis connection initialization, health checks, and availability checks
    that are inherited by all Redis-based services (CacheManager, RateLimiter, etc.).
    """

    _redis_client: Redis | None = None

    def __init__(self):
        # Only initialize Redis in non-local environments
        if settings.current_environment != Environment.LOCAL:
            self._initialize_redis()

    @property
    def redis_client(self) -> Redis | None:
        """
        Get the Redis client instance

        Returns:
            Redis | None: Redis client or None if in local environment
        """
        if settings.current_environment == Environment.LOCAL:
            return None

        if self._redis_client is None:
            raise ValueError("Redis client is not initialized.")

        return self._redis_client

    def _initialize_redis(self):
        """Initialize Redis connection using shared connection pool"""
        try:
            pool = get_redis_pool()
            self._redis_client = Redis(connection_pool=pool)
            logger.debug(
                f"Redis client initialized for {self.__class__.__name__} using shared pool"
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
            logger.error(f"Redis health check failed for {self.__class__.__name__}: {e}")
            return False

    async def close(self):
        """Close Redis connection gracefully"""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info(f"Redis connection closed for {self.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error closing Redis connection for {self.__class__.__name__}: {e}")
