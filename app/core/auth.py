import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Optional
import uuid

import jwt
from fastapi import Request
from passlib.context import CryptContext

from app.core.config import Environment, settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: str | int | uuid.UUID,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT access token
    Args:
        subject: Token subject (usually user ID or username)
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            seconds=settings.access_token_expire_seconds
        )

    to_encode = {"exp": expire, "sub": str(subject), "iat": datetime.now(UTC)}
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(subject: str | int | uuid.UUID) -> str:
    """
    Create JWT refresh token with longer expiration
    Args:
        subject: Token subject (usually user ID or username)

    Returns:
        Encoded JWT refresh token
    """
    expire = datetime.now(UTC) + timedelta(
        seconds=settings.refresh_token_expire_seconds
    )
    to_encode = {"exp": expire, "sub": str(subject), "iat": datetime.now(UTC)}
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hashed password
    Args:
        plain_password: Plain password
        hashed_password: Hashed password

    Returns:
        Whether password matches hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash password
    Args:
        password: Plain password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def generate_random_password(length: int = 12) -> str:
    """
    Generate a random password of specified length
    Args:
        length: Length of the password

    Returns:
        Randomly generated password
    """
    if length < 8:
        raise ValueError("Password length must be at least 8 characters")

    alphabet = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(alphabet) for _ in range(length))


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
