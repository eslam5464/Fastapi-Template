import uuid

from fastapi import Request

from app.core.config import Environment, settings


def parse_user_id(user_id: str | int | uuid.UUID) -> str | int | uuid.UUID:
    """
    Parse user_id to appropriate type

    Args:
        user_id (str | int | uuid.UUID): The user ID to parse

    Returns:
        user_id (str | int | uuid.UUID): Parsed user ID
    """
    if isinstance(user_id, uuid.UUID):
        return user_id

    try:
        return uuid.UUID(str(user_id))
    except ValueError:
        pass

    try:
        return int(user_id)
    except (ValueError, TypeError):
        pass

    return user_id


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
