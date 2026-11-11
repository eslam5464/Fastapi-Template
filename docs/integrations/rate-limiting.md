# Rate limiting

Redis-backed sliding-window rate limiting: the limiter (`app/services/cache/rate_limiter.py`),
the FastAPI dependencies (`app/api/v1/deps/rate_limit.py`), the `X-RateLimit-*` header
middleware (`app/middleware/rate_limit.py`), the key prefixes (`RateLimitPrefix` in
`app/core/constants.py`) and the `RATE_LIMIT_*` settings.

It is included when the project is generated with
`--data services=custom --data include_redis_rate_limit=true` (or by answering "yes" to
the rate limiting question). Without it, no route has a request limit;
put a limit in front of the app (reverse proxy, API gateway) instead.

The template includes a production-ready rate limiting system using Redis and sliding window algorithm.

## Quick Start

Apply pre-configured rate limiters to endpoints using FastAPI dependencies:

```python
from fastapi import APIRouter, Depends
from app.api.v1.deps.rate_limit import (
    rate_limit_auth,    # Strict: 10 req/min (for login, signup)
    rate_limit_api,     # Default: 100 req/min (for general API)
    rate_limit_public,  # Lenient: 1000 req/min (for public data)
)

router = APIRouter()

# IP-based rate limiting for authentication
@router.post("/login", dependencies=[Depends(rate_limit_auth)])
async def login(credentials: LoginForm):
    # Limited to 10 requests per minute per IP
    pass

# IP-based rate limiting for public API
@router.get("/posts", dependencies=[Depends(rate_limit_api)])
async def list_posts():
    # Limited to 100 requests per minute per IP
    pass
```

<!-- --- FEATURE[auth] START --- -->
With authentication, `app/api/v1/deps/rate_limit_user.py` adds limits counted per logged-in user:

```python
from app.api.v1.deps.auth import get_current_user
from app.api.v1.deps.rate_limit_user import rate_limit_user  # 300 req/min per user

# User-based rate limiting for authenticated endpoints
@router.get("/profile", dependencies=[Depends(rate_limit_user)])
async def get_profile(current_user: User = Depends(get_current_user)):
    # Limited to 300 requests per minute per user
    # Multiple users on same IP each get their own quota
    pass
```

<!-- --- FEATURE[auth] END --- -->

## Custom Rate Limits

Create custom rate limiters for specific endpoints:

```python
from app.api.v1.deps.rate_limit import create_rate_limit_ip_only

# Custom limit for heavy operations (5 requests per 5 minutes per IP)
heavy_limit = create_rate_limit_ip_only(limit=5, window=300, prefix="heavy")

@router.post("/export", dependencies=[Depends(heavy_limit)])
async def export_large_file():
    pass
```

<!-- --- FEATURE[auth] START --- -->
With authentication, `create_rate_limit_user_only` and `create_rate_limit_user_and_ip` count per user:

```python
from app.api.v1.deps.rate_limit_user import create_rate_limit_user_only

# Custom user-based limit (20 uploads per minute per user)
upload_limit = create_rate_limit_user_only(limit=20, window=60, prefix="upload")

@router.post("/upload", dependencies=[Depends(upload_limit)])
async def upload_file():
    pass
```

<!-- --- FEATURE[auth] END --- -->

## Rate Limit Response Headers

All rate-limited endpoints automatically include headers in responses:

```http
X-RateLimit-Limit: 100          # Maximum requests allowed
X-RateLimit-Remaining: 73       # Requests remaining in window
X-RateLimit-Reset: 1701234567   # Unix timestamp when limit resets
```

When limit is exceeded, clients receive HTTP 429:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1701234567

{
  "detail": "Rate limit exceeded. Please slow down your requests."
}
```

## Environment Variables

Configure rate limits in `.env`:

```env
# Rate limiting settings
RATE_LIMIT_ENABLED=true     # Enable/disable rate limiting (true/false)
RATE_LIMIT_DEFAULT=100      # General API endpoints (requests per window)
RATE_LIMIT_WINDOW=60        # Time window in seconds
RATE_LIMIT_STRICT=10        # Authentication endpoints
RATE_LIMIT_LENIENT=1000     # Public endpoints
RATE_LIMIT_USER=300         # Authenticated user endpoints
```

## Rate Limiting Strategies

**IP-Based** (for unauthenticated endpoints):

- Login, signup, password reset: 10 req/min per IP
- Public API endpoints: 100 req/min per IP
- Health checks, documentation: 1000 req/min per IP

<!-- --- FEATURE[auth] START --- -->
**User-Based** (for authenticated endpoints):

- User profile, settings: 300 req/min per user
- Solves shared IP problem (office/cafe networks)
- Each user gets independent quota regardless of IP

<!-- --- FEATURE[auth] END --- -->

## Available Prefixes

Rate limit keys use prefixes to separate quotas by endpoint group:

```python
from app.core.constants import RateLimitPrefix

# Pre-defined prefixes
RateLimitPrefix.AUTH      # "ratelimit:auth:"    - Authentication
RateLimitPrefix.USER      # "ratelimit:user:"    - User endpoints
RateLimitPrefix.API       # "ratelimit:api:"     - General API
RateLimitPrefix.PUBLIC    # "ratelimit:public:"  - Public endpoints
RateLimitPrefix.EXPORT    # "ratelimit:export:"  - File exports
RateLimitPrefix.UPLOAD    # "ratelimit:upload:"  - File uploads
RateLimitPrefix.SEARCH    # "ratelimit:search:"  - Search queries
RateLimitPrefix.ADMIN     # "ratelimit:admin:"   - Admin operations
```

Add custom prefixes to `app/core/constants.py` to avoid collisions.

## Local Development

Rate limiting can be controlled via the `RATE_LIMIT_ENABLED` setting:

**To disable rate limiting** (default for local development):

```env
RATE_LIMIT_ENABLED=false
```

- No Redis connection required
- All requests allowed (no limits enforced)
- Useful for development without Redis setup

**To test rate limiting locally**:

```env
RATE_LIMIT_ENABLED=true
CURRENT_ENVIRONMENT=local
```

- Requires Redis to be running
- Full rate limiting functionality available
- Test rate limits before deploying to production

## High-Frequency Requests

The rate limiter uses **microsecond precision** for timestamp tracking:

- Accurately counts multiple requests within the same second
- Prevents duplicate member issues in Redis sorted sets
- Supports high-frequency API usage (e.g., real-time applications)
- Each request gets a unique identifier: `{microseconds}:{hash}`

## API reference

The API implements production-ready rate limiting using Redis with a sliding window algorithm and microsecond precision.

### Rate Limit Tiers

| Endpoint Type                        | Limit    | Window | Description          |
| ------------------------------------ | -------- | ------ | -------------------- |
| Authentication (`/login`, `/signup`) | 10 req   | 1 min  | Strict limit per IP  |
| General API                          | 100 req  | 1 min  | Default limit per IP |
| Public endpoints                     | 1000 req | 1 min  | Lenient limit per IP |

<!-- --- FEATURE[auth] START --- -->
Authenticated user endpoints: 300 requests per minute, counted per user ID.

<!-- --- FEATURE[auth] END --- -->
### Rate Limit Response Headers

All rate-limited endpoints include these headers:

```http
X-RateLimit-Limit: 100          # Maximum requests allowed
X-RateLimit-Remaining: 73       # Requests remaining in window
X-RateLimit-Reset: 1701234567   # Unix timestamp when limit resets
```

### Rate Limit Exceeded Response

When the limit is exceeded, clients receive HTTP 429:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1701234567
```

```json
{
  "detail": "Rate limit exceeded. Please slow down your requests."
}
```

### Configuration

Rate limiting can be configured via environment variables:

```env
RATE_LIMIT_ENABLED=true     # Enable/disable rate limiting
RATE_LIMIT_DEFAULT=100      # General API endpoints
RATE_LIMIT_WINDOW=60        # Time window in seconds
RATE_LIMIT_STRICT=10        # Authentication endpoints
RATE_LIMIT_LENIENT=1000     # Public endpoints
RATE_LIMIT_USER=300         # Authenticated user endpoints
```

**Note**: Rate limiting requires Redis. If Redis is unavailable, the system fails open (allows requests) to prevent service disruption
