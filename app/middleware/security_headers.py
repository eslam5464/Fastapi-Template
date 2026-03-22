from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Environment, settings

DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data: https:; "
    "font-src 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "base-uri 'self'"
)

DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com "
    "https://fonts.googleapis.com; "
    "img-src 'self' data: https:; "
    "font-src 'self' https://fonts.gstatic.com https://fonts.googleapis.com; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "base-uri 'self'; "
    "worker-src 'self' blob:"
)

DOCS_PATH_PREFIXES = (
    "/v1/docs",
    "/v1/redoc",
    "/v2/docs",
    "/v2/redoc",
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    These headers help protect against common web vulnerabilities
    as recommended by OWASP Security Headers Cheat Sheet.

    Implements OWASP recommended security headers:
        - X-Content-Type-Options: Prevents MIME-type sniffing
        - X-Frame-Options: Prevents clickjacking attacks
        - X-XSS-Protection: Enables browser XSS filtering (legacy)
        - Strict-Transport-Security: Enforces HTTPS
        - Content-Security-Policy: Controls resource loading
        - Referrer-Policy: Controls referrer information
        - Permissions-Policy: Controls browser features

    Reference: https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html
    """

    @staticmethod
    def _get_request_path(request: Request) -> str:
        """Extract request path safely for mocked requests in tests."""
        url = getattr(request, "url", None)
        if not url:
            return ""
        return getattr(url, "path", "") or ""

    @staticmethod
    def _is_docs_ui_path(path: str) -> bool:
        """Check whether a request targets versioned Swagger/ReDoc endpoints."""
        return any(path.startswith(prefix) for prefix in DOCS_PATH_PREFIXES)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)
        request_path = self._get_request_path(request)

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking - deny all framing
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Disable unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        # HSTS - Only in production environments with HTTPS
        if settings.current_environment in {Environment.STG, Environment.PRD}:
            # max-age=31536000 (1 year), includeSubDomains for all subdomains
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Use a docs-friendly CSP only for Swagger/ReDoc routes.
        response.headers["Content-Security-Policy"] = (
            DOCS_CSP if self._is_docs_ui_path(request_path) else DEFAULT_CSP
        )

        # Prevent caching of sensitive responses (can be overridden per-endpoint)
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        return response
