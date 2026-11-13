from typing import Any

from fastapi import Request, status

from app.core import responses
from app.core.config import settings
from app.core.exceptions.http_exceptions import TooManyRequestsException
from app.core.utils import get_client_ip
from app.services.cache.rate_limiter import RateLimitPrefix, rate_limiter


def rate_limit_responses(limit: int, reset_example: int = 1764425820102866) -> dict[int | str, dict[str, Any]]:
    """
    OpenAPI `responses` entry documenting the 429 a rate-limited route can return.

    Spread it into a route's `responses` (`**rate_limit_responses(60)`) or pass
    it whole to `include_router(responses=...)`.

    Args:
        limit: Requests allowed per minute, shown in the header descriptions.
        reset_example: Example value of the X-RateLimit-Reset header.

    Returns:
        A dict keyed by status 429 with the response model and rate limit headers.
    """
    return {
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": responses.TooManyRequestsResponse,
            "headers": {
                "X-RateLimit-Limit": {
                    "description": f"Maximum requests allowed ({limit}/min)",
                    "schema": {"type": "integer", "example": limit},
                },
                "X-RateLimit-Remaining": {
                    "description": "Requests remaining in current window",
                    "schema": {"type": "integer", "example": limit - 1},
                },
                "X-RateLimit-Reset": {
                    "description": "Unix timestamp when limit resets",
                    "schema": {"type": "integer", "example": reset_example},
                },
            },
        },
    }


# The 429 response of the auth routes, which all share rate_limit_auth.
RATE_LIMIT_AUTH_RESPONSES = rate_limit_responses(limit=10, reset_example=17655251150102866)


async def rate_limit_auth(request: Request) -> None:
    """
    Strict rate limiting for authentication endpoints (login, signup, password reset).

    - **Limit:** 10 requests per minute per IP
    - **Strategy:** IP-based
    - **Use case:** Prevents brute force attacks on authentication endpoints

    Args:
        request: FastAPI request object

    Raises:
        TooManyRequestsException: When rate limit is exceeded
    """
    ip = get_client_ip(request)
    key = f"{RateLimitPrefix.AUTH}{ip}"

    is_allowed, info = await rate_limiter.check_rate_limit(
        key=key,
        limit=settings.rate_limit_strict,
        window=settings.rate_limit_window,
    )

    # Store info in request state for middleware
    request.state.rate_limit_info = info

    if not is_allowed:
        raise TooManyRequestsException(
            detail="Rate limit exceeded. Too many requests.",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset_time"]),
            },
        )


async def rate_limit_api(request: Request) -> None:
    """
    Moderate rate limiting for general API endpoints.

    - **Limit:** 100 requests per minute per IP
    - **Strategy:** IP-based
    - **Use case:** Standard API protection for public endpoints

    Args:
        request: FastAPI request object

    Raises:
        TooManyRequestsException: When rate limit is exceeded
    """
    ip = get_client_ip(request)
    key = f"{RateLimitPrefix.API}{ip}"

    is_allowed, info = await rate_limiter.check_rate_limit(
        key=key,
        limit=settings.rate_limit_default,
        window=settings.rate_limit_window,
    )

    request.state.rate_limit_info = info

    if not is_allowed:
        raise TooManyRequestsException(
            detail="Rate limit exceeded. Too many requests.",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset_time"]),
            },
        )


async def rate_limit_public(request: Request) -> None:
    """
    Lenient rate limiting for public/read-only endpoints.

    - **Limit:** 1000 requests per minute per IP
    - **Strategy:** IP-based
    - **Use case:** Public endpoints like health checks, documentation

    Args:
        request: FastAPI request object

    Raises:
        TooManyRequestsException: When rate limit is exceeded
    """
    ip = get_client_ip(request)
    key = f"{RateLimitPrefix.PUBLIC}{ip}"

    is_allowed, info = await rate_limiter.check_rate_limit(
        key=key,
        limit=settings.rate_limit_lenient,
        window=settings.rate_limit_window,
    )

    request.state.rate_limit_info = info

    if not is_allowed:
        raise TooManyRequestsException(
            detail="Rate limit exceeded. Too many requests.",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset_time"]),
            },
        )


def create_rate_limit_ip_only(limit: int, window: int = 60, prefix: str = "custom"):
    """
    Factory function to create custom rate limiter with specific limits.

    Args:
        limit: Maximum requests allowed in the time window
        window: Time window in seconds (default: 60)
        prefix: Custom prefix for Redis key (will be prepended with "ratelimit:")

    Returns:
        Async dependency function for rate limiting

    Example:
        ```python
        # Create custom rate limiter for file exports (5 requests per 5 minutes)
        export_limit = create_rate_limit(limit=5, window=300, prefix="export")

        @router.post("/export", dependencies=[Depends(export_limit)])
        async def export_data(...):
            pass
        ```
    """
    full_prefix = f"ratelimit:{prefix}:"

    async def custom_rate_limiter(request: Request) -> None:
        ip = get_client_ip(request)
        key = f"{full_prefix}{ip}"

        is_allowed, info = await rate_limiter.check_rate_limit(
            key=key,
            limit=limit,
            window=window,
        )

        request.state.rate_limit_info = info

        if not is_allowed:
            raise TooManyRequestsException(
                detail="Rate limit exceeded. Too many requests.",
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset": str(info["reset_time"]),
                },
            )

    return custom_rate_limiter
