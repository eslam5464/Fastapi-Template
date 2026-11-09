# Caching (Redis)

`app/services/cache/manager.py` provides `cache_manager`, a Redis-backed cache for any
picklable Python object, and `app/services/cache/decorators.py` provides the
`cache_result` decorator. Both share the project's Redis connection pool
(`app/services/cache/base.py`).

The cache is included when the project is generated with
`--data services=custom --data include_redis_cache=true` (or by answering "yes" to the
cache question). Choosing it (or rate limiting, the token blacklist or Celery) also adds
Redis: the `redis` dependency, the `REDIS_*` settings, and the Redis service in
`docker-compose.yml` and in the generated CI.

## Configuration

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_USER=redis_user
REDIS_PASS=your-redis-password
REDIS_BASE=0

CACHE_ENABLED=False        # when true, startup fails if Redis is unreachable
CACHE_TTL_DEFAULT=300      # seconds
CACHE_TTL_SHORT=60
CACHE_TTL_LONG=3600
CACHE_TTL_VERY_LONG=86400
```

In the `LOCAL` environment the Redis clients are inert, so the cache always misses and
writes are no-ops. Elsewhere, Redis errors are logged and treated as cache misses.

## Usage

```python
from app.core.config import settings
from app.services.cache.manager import cache_manager

await cache_manager.set("user:42:profile", profile, expire=settings.cache_ttl_short)
profile = await cache_manager.get("user:42:profile")  # None on a miss
await cache_manager.delete("user:42:profile")
deleted = await cache_manager.delete_pattern("user:42:*")
exists = await cache_manager.exists("user:42:profile")
```

```python
from app.services.cache.decorators import cache_result


@cache_result(expire=300, key_prefix="reports")
async def build_report(org_id: int) -> dict:
    ...
```

`cache_result` caches the return value under `"<key_prefix>:<function name>:<hash of the
arguments>"`. Values are stored with `pickle`, so only cache data your own code
produced, never anything a client can write into Redis.

## Production

- Use a password and a dedicated ACL user (the compose file creates one from
  `REDIS_USER` / `REDIS_PASS`) and keep Redis off the public network
- Set `CACHE_ENABLED=true` if the app must not start without a working cache
- Give each environment its own Redis database (`REDIS_BASE`) or instance
