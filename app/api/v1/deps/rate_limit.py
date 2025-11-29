from typing import Annotated

from fastapi import Depends, Request

from app.api.v1.deps.auth import get_current_user
from app.core.config import settings
from app.core.constants import RateLimitPrefix
from app.core.exceptions.http_exceptions import TooManyRequestsException
from app.core.utils import get_client_ip
from app.models.user import User
from app.services.cache import rate_limiter


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


async def rate_limit_user(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = settings.rate_limit_user,
    window: int = settings.rate_limit_window,
) -> None:
    """
    Rate limiting for authenticated user endpoints.

    - **Limit:** 300 requests per minute per user
    - **Strategy:** User ID-based (independent of IP address)
    - **Use case:** Authenticated endpoints where fair per-user limits are needed

    Args:
        request: FastAPI request object
        current_user: Currently authenticated user

    Raises:
        TooManyRequestsException: When rate limit is exceeded
    """
    key = f"{RateLimitPrefix.USER}{current_user.id}"

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


def create_rate_limit_user_only(limit: int, window: int = 60, prefix: str = "custom"):
    """
    Factory function to create custom rate limiter for authenticated users.

    Args:
        limit: Maximum requests allowed in the time window
        window: Time window in seconds (default: 60)
        prefix: Custom prefix for Redis key (will be prepended with "ratelimit:user:")

    Returns:
        Async dependency function for user-based rate limiting

    Example:
        ```python
        # Create custom rate limiter for data uploads (20 requests per 10 minutes)
        upload_limit = create_rate_limit_user_only(limit=20, window=600, prefix="upload")

        @router.post("/upload", dependencies=[Depends(upload_limit)])
        async def upload_data(...):
            pass
        ```
    """
    full_prefix = f"ratelimit:user:{prefix}:"

    async def custom_user_rate_limiter(
        request: Request,
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> None:
        key = f"{full_prefix}{current_user.id}"

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

    return custom_user_rate_limiter


def create_rate_limit_user_and_ip(limit: int, window: int = 60, prefix: str = "custom"):
    """
    Factory function to create custom rate limiter that combines user ID and IP address.

    Args:
        limit: Maximum requests allowed in the time window
        window: Time window in seconds (default: 60)
        prefix: Custom prefix for Redis key (will be prepended with "ratelimit:userip:")

    Returns:
        Async dependency function for combined user and IP-based rate limiting

    Example:
        ```python
        # Create custom rate limiter for sensitive actions (15 requests per 10 minutes)
        sensitive_limit = create_rate_limit_user_and_ip(limit=15, window=600, prefix="sensitive")

        @router.post("/sensitive-action", dependencies=[Depends(sensitive_limit)])
        async def sensitive_action(...):
            pass
        ```
    """
    full_prefix = f"ratelimit:userip:{prefix}:"

    async def custom_user_ip_rate_limiter(
        request: Request,
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> None:
        ip = get_client_ip(request)
        key = f"{full_prefix}{current_user.id}:{ip}"

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

    return custom_user_ip_rate_limiter


def create_rate_limit(
    limit: int,
    window: int = 60,
    prefix: str = "custom",
    user_based: bool = False,
):
    """
    Factory function to create custom rate limiter.

    Args:
        limit: Maximum requests allowed in the time window
        window: Time window in seconds (default: 60)
        prefix: Custom prefix for Redis key (will be prepended with "ratelimit:" or "ratelimit:user:")
        user_based: If True, rate limit is based on authenticated user ID; if False, based on IP
    Returns:
        Async dependency function for rate limiting
    Example:
        ```python
        # Create custom rate limiter for file exports (5 requests per 5 minutes)
        export_limit = create_rate_limit(limit=5, window=300, prefix="export", user_based=False)

        @router.post("/export", dependencies=[Depends(export_limit)])
        async def export_data(...):
            pass
        ```
    """
    if user_based:
        return create_rate_limit_user_only(limit=limit, window=window, prefix=prefix)
    else:
        return create_rate_limit_ip_only(limit=limit, window=window, prefix=prefix)
