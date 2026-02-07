import time
import uuid
from typing import Any, Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, _StreamingResponse

# Sensitive fields that should be redacted from logs
# Reference: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
SENSITIVE_FIELDS = {
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "refresh_token",
    "access_token",
    "credit_card",
    "card_number",
    "cvv",
    "ssn",
    "private_key",
}


def sanitize_body(body: dict[str, Any] | Any) -> dict[str, Any] | Any:
    """
    Recursively sanitize sensitive fields from request body before logging.

    Args:
        body: The request body to sanitize

    Returns:
        Sanitized body with sensitive fields redacted
    """
    if not isinstance(body, dict):
        return body

    sanitized = {}
    for key, value in body.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_body(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_body(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())[:8]

        # Add request ID to request state
        request.state.request_id = request_id

        start_time = time.time()

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Log request with more details
        logger.trace(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Client: {client_ip} - User-Agent: {request.headers.get('user-agent', 'unknown')}",
            request_id=request_id,
        )

        try:
            response: _StreamingResponse = await call_next(request)

            # Log response
            process_time = time.time() - start_time
            logger.trace(
                f"[{request_id}] {request.method} {request.url.path} - "
                f"Status: {response.status_code} - Time: {process_time:.3f}s",
                request_id=request_id,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            process_time = time.time() - start_time

            try:
                json_body = await request.json()
                # Sanitize sensitive data before logging
                json_body = sanitize_body(json_body)
            except Exception:
                json_body = ""

            error_msg = (
                f"[{request_id}] {request.method} {request.url.path} - "
                f"Error: {str(e)} - Time: {process_time:.3f}s"
            )
            logger.error(
                error_msg,
                request_id=request_id,
                request_body=json_body,
                request_query_params=dict(request.query_params),
                request_path_params=request.path_params,
            )
            raise e
