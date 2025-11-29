from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitHeaderMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically add rate limit headers to responses.

    This middleware checks if rate limiting was performed on the request
    (by checking request.state.rate_limit_info) and adds the appropriate
    headers to the response.

    The middleware only adds headers when:
    1. A rate limit dependency was used on the endpoint
    2. The dependency stored rate_limit_info in request.state

    This hybrid approach provides:
    - Performance: Only checks rate limit when dependency is applied
    - Automatic headers: No manual response manipulation needed
    - Clean separation: Dependencies do checking, middleware adds headers

    Example:
        ```python
        # In app/main.py
        from app.middleware.rate_limit import RateLimitHeaderMiddleware

        app.add_middleware(RateLimitHeaderMiddleware)
        ```
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and add rate limit headers if available.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response with rate limit headers (if rate limiting was checked)
        """
        # Call the next middleware/handler
        response: Response = await call_next(request)

        # Check if rate limit info was stored by a dependency
        if hasattr(request.state, "rate_limit_info"):
            info = request.state.rate_limit_info

            # Add rate limit headers to response
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset_time"])

        return response
