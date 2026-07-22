from functools import wraps
from typing import Any, Callable

from app.core.config import settings


def cache_result(expire: int = settings.cache_ttl_default, key_prefix: str = "") -> Callable:
    """Decorator to cache function results"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            from app.services.cache import cache_manager

            # Generate cache key
            cache_key = (
                f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            )

            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)

            if cached_result is not None:
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await cache_manager.set(cache_key, result, expire)
            return result

        return wrapper

    return decorator
