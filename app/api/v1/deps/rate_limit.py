from fastapi import Request
from loguru import logger

from app.core.config import settings
from app.core.constants import RateLimitPrefix
from app.core.exceptions.http_exceptions import TooManyRequestsException
from app.core.utils import get_client_ip
from app.models.user import User
from app.services.cache.rate_limiter import rate_limiter


async def rate_limit_auth(request: Request) -> None:
    """
    Strict rate limiting for authentication endpoints (IP-based).

    Apply this to sensitive endpoints like login, signup, and password reset
    to prevent brute force attacks.

    Limit: 10 requests per minute per IP (configurable via settings.rate_limit_strict)
    Key strategy: IP address
    Use case: Login, signup, password reset, forgot password

    Args:
        request: FastAPI request object

    Raises:
        TooManyRequestsException: When rate limit is exceeded (HTTP 429)

    Example:
        ```python
        @router.post("/login", dependencies=[Depends(rate_limit_auth)])
        async def login(...):
            pass
        ```
    """
    ip = get_client_ip(request)
    key = f"{RateLimitPrefix.AUTH}{ip}"

    is_allowed, info = await rate_limiter.check_rate_limit(
        key=key, limit=settings.rate_limit_strict, window=settings.rate_limit_window
    )

    # Store rate limit info in request state for middleware
    request.state.rate_limit_info = info

    if not is_allowed:
        logger.warning(f"Rate limit exceeded for authentication endpoint. IP: {ip}, Key: {key}")
        raise TooManyRequestsException(
            detail="Too many authentication attempts. Please try again later.",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset_time"]),
            },
        )


async def rate_limit_api(request: Request) -> None:
    """
    Moderate rate limiting for general API endpoints (IP-based).

    Apply this to standard API operations that don't require authentication
    but need reasonable protection against abuse.

    Limit: 100 requests per minute per IP (configurable via settings.rate_limit_default)
    Key strategy: IP address
    Use case: Public API endpoints, general operations

    Args:
        request: FastAPI request object

    Raises:
        TooManyRequestsException: When rate limit is exceeded (HTTP 429)

    Example:
        ```python
        @router.get("/posts", dependencies=[Depends(rate_limit_api)])
        async def list_posts(...):
            pass
        ```
    """
    ip = get_client_ip(request)
    key = f"{RateLimitPrefix.API}{ip}"

    is_allowed, info = await rate_limiter.check_rate_limit(
        key=key, limit=settings.rate_limit_default, window=settings.rate_limit_window
    )

    request.state.rate_limit_info = info

    if not is_allowed:
        logger.warning(f"Rate limit exceeded for API endpoint. IP: {ip}, Key: {key}")
        raise TooManyRequestsException(
            detail="Rate limit exceeded. Please slow down your requests.",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset_time"]),
            },
        )


async def rate_limit_public(request: Request) -> None:
    """
    Lenient rate limiting for public endpoints (IP-based).

    Apply this to read-heavy public endpoints that need minimal protection.
    Suitable for health checks, documentation, and public data.

    Limit: 1000 requests per minute per IP (configurable via settings.rate_limit_lenient)
    Key strategy: IP address
    Use case: Health checks, public read-only data, documentation

    Args:
        request: FastAPI request object

    Raises:
        TooManyRequestsException: When rate limit is exceeded (HTTP 429)

    Example:
        ```python
        @router.get("/health", dependencies=[Depends(rate_limit_public)])
        async def health_check():
            pass
        ```
    """
    ip = get_client_ip(request)
    key = f"{RateLimitPrefix.PUBLIC}{ip}"

    is_allowed, info = await rate_limiter.check_rate_limit(
        key=key, limit=settings.rate_limit_lenient, window=settings.rate_limit_window
    )

    request.state.rate_limit_info = info

    if not is_allowed:
        logger.warning(f"Rate limit exceeded for public endpoint. IP: {ip}, Key: {key}")
        raise TooManyRequestsException(
            detail="Rate limit exceeded. Please slow down your requests.",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset_time"]),
            },
        )


async def rate_limit_user(request: Request, current_user: User) -> None:
    """
    User-based rate limiting for authenticated endpoints.

    Apply this to authenticated user endpoints where each user should have
    their own independent rate limit quota. This prevents shared IP issues
    (e.g., multiple users in the same office).

    Limit: 300 requests per minute per user (configurable via settings.rate_limit_user)
    Key strategy: User ID (not IP)
    Use case: User profile, user posts, user settings, authenticated operations

    Args:
        request: FastAPI request object
        current_user: Authenticated user from get_current_user dependency

    Raises:
        TooManyRequestsException: When rate limit is exceeded (HTTP 429)

    Note:
        This dependency requires the current_user to be injected by FastAPI.
        It will be automatically resolved from the get_current_user dependency.

    Example:
        ```python
        from app.api.v1.deps.auth import get_current_user
        from app.api.v1.deps.rate_limit import rate_limit_user

        @router.get("/profile", dependencies=[Depends(rate_limit_user)])
        async def get_profile(current_user: User = Depends(get_current_user)):
            # current_user is available here and in rate_limit_user
            pass
        ```
    """
    key = f"{RateLimitPrefix.USER}{current_user.id}"

    is_allowed, info = await rate_limiter.check_rate_limit(
        key=key, limit=settings.rate_limit_user, window=settings.rate_limit_window
    )

    request.state.rate_limit_info = info

    if not is_allowed:
        logger.warning(
            f"Rate limit exceeded for user endpoint. User ID: {current_user.id}, Key: {key}"
        )
        raise TooManyRequestsException(
            detail="Rate limit exceeded. Please slow down your requests.",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset_time"]),
            },
        )


def create_rate_limit(
    limit: int, window: int = 60, prefix: str = "custom", use_user_id: bool = False
):
    """
    Factory function to create custom rate limiters with specific limits.

    Use this when you need endpoint-specific rate limits that differ from
    the pre-configured options (auth, api, public, user).

    Args:
        limit: Maximum number of requests allowed in the time window
        window: Time window in seconds (default: 60)
        prefix: Custom prefix for the rate limit key (without "ratelimit:" and ":")
        use_user_id: If True, use user ID instead of IP for rate limiting (default: False)

    Returns:
        Async dependency function that can be used with Depends()

    Raises:
        ValueError: If prefix conflicts with existing prefixes

    Example:
        ```python
        # Create custom rate limiter for file exports (5 per 5 minutes)
        file_export_limit = create_rate_limit(limit=5, window=300, prefix="export")

        @router.post("/export", dependencies=[Depends(file_export_limit)])
        async def export_data(...):
            pass

        # Create user-based custom rate limiter for heavy operations
        heavy_operation_limit = create_rate_limit(
            limit=10,
            window=60,
            prefix="heavy",
            use_user_id=True
        )

        @router.post("/heavy-task", dependencies=[Depends(heavy_operation_limit)])
        async def heavy_task(current_user: User = Depends(get_current_user)):
            pass
        ```
    """
    # Validate prefix doesn't conflict
    full_prefix = f"ratelimit:{prefix}:"
    from app.core.constants import RateLimitPrefix

    RateLimitPrefix.validate_prefix(full_prefix)

    if use_user_id:
        # User-based rate limiting
        async def custom_user_limiter(request: Request, current_user: User) -> None:
            key = f"{full_prefix}{current_user.id}"

            is_allowed, info = await rate_limiter.check_rate_limit(
                key=key, limit=limit, window=window
            )

            request.state.rate_limit_info = info

            if not is_allowed:
                logger.warning(
                    f"Rate limit exceeded for custom endpoint. User ID: {current_user.id}, "
                    f"Prefix: {prefix}, Key: {key}"
                )
                raise TooManyRequestsException(
                    detail="Rate limit exceeded. Please slow down your requests.",
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset_time"]),
                    },
                )

        return custom_user_limiter
    else:
        # IP-based rate limiting
        async def custom_ip_limiter(request: Request) -> None:
            ip = get_client_ip(request)
            key = f"{full_prefix}{ip}"

            is_allowed, info = await rate_limiter.check_rate_limit(
                key=key, limit=limit, window=window
            )

            request.state.rate_limit_info = info

            if not is_allowed:
                logger.warning(
                    f"Rate limit exceeded for custom endpoint. IP: {ip}, "
                    f"Prefix: {prefix}, Key: {key}"
                )
                raise TooManyRequestsException(
                    detail="Rate limit exceeded. Please slow down your requests.",
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset_time"]),
                    },
                )

        return custom_ip_limiter
