from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Environment, settings


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

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)

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

        # Content Security Policy - restrictive default
        # Adjust based on your application's needs (fonts, images, scripts sources)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "  # Allow inline for Swagger UI
            "style-src 'self' 'unsafe-inline'; "  # Allow inline for Swagger UI
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'"
        )

        # Prevent caching of sensitive responses (can be overridden per-endpoint)
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        return response
