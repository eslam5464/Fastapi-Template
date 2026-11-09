import hashlib
from functools import wraps
from typing import Any, Callable

from app.core.config import settings


def build_cache_key(key_prefix: str, func: Callable, args: tuple, kwargs: dict) -> str:
    """
    Cache key for one call of `func`.

    The same arguments give the same key in every process (every worker and after
    every restart), so cached results are shared. Python's built-in hash() would
    not do: it is randomized per process for strings. The function is identified by
    its module and qualified name, so functions with the same name in different
    modules do not share entries.

    Arguments are identified by their repr(), so they should have stable reprs
    (numbers, strings, UUIDs, enums, Pydantic models, dataclasses...). An object
    with the default repr (which contains its memory address) gives a different
    key for every instance, so such calls are never served from the cache.
    """
    arguments = repr(args) + repr(sorted(kwargs.items()))
    digest = hashlib.sha256(arguments.encode("utf-8")).hexdigest()
    return f"{key_prefix}:{func.__module__}.{func.__qualname__}:{digest}"


def cache_result(expire: int = settings.cache_ttl_default, key_prefix: str = "") -> Callable:
    """Decorator to cache function results"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            from app.services.cache import cache_manager

            cache_key = build_cache_key(key_prefix, func, args, kwargs)

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
