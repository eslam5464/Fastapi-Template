import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app import repos
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.core.config import settings
from app.core.db import get_session
from app.core.exceptions import http_exceptions
from app.core.utils import parse_user_id
from app.models.user import User
from app.schemas import TokenData, TokenPayload, UserCreate, UserSignup

# OAuth2 password bearer scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """
    Get current authenticated user from JWT token

    Args:
        token: JWT token
        db: Database session

    Returns:
        Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = http_exceptions.UnauthorizedException(
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    credentials_expired = http_exceptions.UnauthorizedException(
        detail="Token has expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    credentials_claims_error = http_exceptions.UnauthorizedException(
        detail="Token has invalid claims",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token=token,
            key=settings.secret_key,
            algorithms=settings.jwt_algorithm,
        )

        user_id: str | int | uuid.UUID | None = payload.get("sub")
        expires_at: int | None = payload.get("exp")

        if user_id is None or expires_at is None:
            raise credentials_exception

        token_data = TokenData(
            user_id=parse_user_id(user_id),
            issued_at=payload.get("iat"),
            expires_at=expires_at,
        )

    except JWTClaimsError:
        raise credentials_claims_error
    except ExpiredSignatureError:
        raise credentials_expired
    except JWTError:
        raise credentials_exception

    now = int(datetime.now(UTC).timestamp())

    if token_data.expires_at is not None and now > token_data.expires_at:
        raise credentials_expired

    user = await repos.UserRepo(db).get_by_id(token_data.user_id)

    if user is None:
        raise credentials_exception

    return user


async def generate_access_token(
    user_in: Annotated[UserSignup, Form()],
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """
    Generate new access token using the provided refresh token.

    Args:
        token_payload: Payload containing the refresh token.
        db: Database session.

    Returns:
        A dictionary with new access token.

    Raises:
        BadRequestException: If the refresh token is invalid or user not found.
    """
    user = await repos.UserRepo(db).get_by_email(email=user_in.email)
    if user:
        raise http_exceptions.BadRequestException(
            detail="A user with this email already exists.",
        )

    user_hashed_password = get_password_hash(user_in.password.get_secret_value())
    user = await repos.UserRepo(db).create_one(
        schema=UserCreate(
            first_name="",
            last_name="",
            username=user_in.username,
            email=user_in.email,
            hashed_password=user_hashed_password,
        ),
    )
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


async def generate_refresh_token(
    token_payload: TokenPayload,
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """
    Generate new access and refresh tokens using the provided refresh token.

    Args:
        token_payload: Payload containing the refresh token.
        db: Database session.

    Returns:
        A dictionary with new access and refresh tokens.

    Raises:
        UnauthorizedException: If the refresh token is invalid or user not found.
    """
    try:
        payload = jwt.decode(
            token_payload.refresh_token,
            settings.secret_key,
            algorithms=settings.jwt_algorithm,
        )
        user_id: str | int | uuid.UUID | None = payload.get("sub")

        if user_id is None:
            raise http_exceptions.UnauthorizedException(
                "Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = parse_user_id(user_id)
    except JWTError:
        raise http_exceptions.UnauthorizedException(
            "Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await repos.UserRepo(db).get_by_id(user_id)
    if not user:
        raise http_exceptions.UnauthorizedException(
            "Invalid user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


async def login_user_for_access_token(
    user_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """
    OAuth2 compatible token login, get an access token for future requests

    Args:
        user_data: OAuth2 password request form data
        db: Database session

    Returns:
        A dictionary with access and refresh tokens

    Raises:
        UnauthorizedException: If username or password is incorrect
    """
    user = await repos.UserRepo(db).get_by_username(username=user_data.username)

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise http_exceptions.UnauthorizedException(
            "Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(subject=str(user.id)),
        "refresh_token": create_refresh_token(subject=str(user.id)),
    }
