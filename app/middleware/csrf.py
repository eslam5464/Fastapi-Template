import secrets
from typing import Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Environment, settings
from app.core.exceptions import http_exceptions

# Token settings
CSRF_TOKEN_LENGTH = 32
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

# Safe HTTP methods that don't require CSRF protection
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

# Paths exempt from CSRF protection (auth endpoints using JWT)
EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/signup",
    "/api/v1/auth/refresh-token",
    "/api/v1/auth/logout",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware implementing header-based CSRF protection.

    For state-changing requests (POST, PUT, DELETE, PATCH):
    1. Validates that X-CSRF-Token header matches the csrf_token cookie
    2. Generates new CSRF token for responses if none exists

    Safe methods (GET, HEAD, OPTIONS) and exempt paths are not validated.

    Implements header-based CSRF protection for state-changing requests.
    Uses double-submit cookie pattern with X-CSRF-Token header validation.

    Reference: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
    """

    def _is_exempt(self, request: Request) -> bool:
        """Check if the request path is exempt from CSRF protection."""
        path = request.url.path

        # Exact match
        if path in EXEMPT_PATHS:
            return True

        # Check if path starts with any exempt prefix (for swagger assets, etc.)
        exempt_prefixes = ("/docs", "/redoc", "/openapi")
        return any(path.startswith(prefix) for prefix in exempt_prefixes)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip CSRF in local environment for easier development
        if settings.current_environment == Environment.LOCAL:
            response = await call_next(request)
            return response

        # Safe methods don't need CSRF protection
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            # Ensure CSRF cookie is set for subsequent requests
            self._ensure_csrf_cookie(request, response)
            return response

        # Exempt paths don't need CSRF protection
        if self._is_exempt(request):
            response = await call_next(request)
            return response

        # Validate CSRF token for state-changing requests
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)

        if not cookie_token or not header_token:
            logger.warning(
                f"CSRF validation failed - missing tokens. "
                f"Cookie present: {bool(cookie_token)}, Header present: {bool(header_token)}, "
                f"Path: {request.url.path}"
            )
            raise http_exceptions.ForbiddenException(
                detail="CSRF token missing. Include X-CSRF-Token header matching csrf_token cookie."
            )

        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(cookie_token, header_token):
            logger.warning(f"CSRF validation failed - token mismatch. Path: {request.url.path}")
            raise http_exceptions.ForbiddenException(detail="CSRF token validation failed.")

        response = await call_next(request)
        return response

    def _ensure_csrf_cookie(self, request: Request, response: Response) -> None:
        """Ensure CSRF cookie is set if not present."""
        if CSRF_COOKIE_NAME not in request.cookies:
            csrf_token = generate_csrf_token()

            # Set secure cookie attributes
            secure = settings.current_environment in {Environment.STG, Environment.PRD}

            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=csrf_token,
                httponly=False,  # Must be readable by JavaScript
                secure=secure,
                samesite="strict",
                max_age=3600,  # 1 hour
                path="/",
            )
