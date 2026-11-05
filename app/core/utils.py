from fastapi import Request

from app.core.config import Environment, settings


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request headers or remote address

    Args:
        request: FastAPI request object

    Returns:
        Client IP address as a string
    """
    if settings.current_environment == Environment.LOCAL:
        return "localhost"

    if "X-Forwarded-For" in request.headers:
        return request.headers["X-Forwarded-For"].split(",")[0].strip()

    if "X-Real-IP" in request.headers:
        return request.headers["X-Real-IP"].strip()

    if "X-Client-IP" in request.headers:
        return request.headers["X-Client-IP"].strip()

    return request.client.host if request.client else "unknown"
