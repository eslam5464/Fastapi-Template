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
from app.core.types import TokenPairDict
from app.core.utils import parse_user_id
from app.models.user import User
from app.schemas import TokenData, TokenPayload, UserCreate, UserSignup
from app.services.cache.token_blacklist import token_blacklist

# OAuth2 password bearer scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Pre-computed dummy hash for timing attack prevention
# Reference: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
_DUMMY_HASH = get_password_hash("dummy_password_for_timing_attack_prevention")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """
    Get current authenticated user from JWT token.

    Validates:
    - Token signature and expiration
    - Token type is "access" (not refresh token)
    - Token is not revoked (blacklisted)
    - User exists in database

    Args:
        token: JWT token
        db: Database session

    Returns:
        Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found

    Reference:
        https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
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

    token_revoked = http_exceptions.UnauthorizedException(
        detail="Token has been revoked",
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
        token_type: str | None = payload.get("type")
        jti: str | None = payload.get("jti")
        issued_at: int | None = payload.get("iat")

        if user_id is None or expires_at is None:
            raise credentials_exception

        # Validate token type - must be "access" token
        if token_type != "access":
            raise credentials_claims_error

        # Check if token is blacklisted (revoked)
        if jti and await token_blacklist.is_revoked(jti):
            raise token_revoked

        token_data = TokenData(
            user_id=parse_user_id(user_id),
            issued_at=issued_at,
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

    # Check if all user tokens were revoked (e.g., password change)
    revocation_time = await token_blacklist.get_user_revocation_time(str(token_data.user_id))
    if revocation_time and issued_at and issued_at < revocation_time:
        raise token_revoked

    user = await repos.UserRepo(db).get_by_id(token_data.user_id)

    if user is None:
        raise credentials_exception

    return user


async def generate_access_token(
    user_in: Annotated[UserSignup, Form()],
    db: AsyncSession = Depends(get_session),
) -> TokenPairDict:
    """
    Generate new access token using the provided refresh token.

    Args:
        token_payload: Payload containing the refresh token.
        db: Database session.

    Returns:
        TokenPairDict with access and refresh tokens.

    Raises:
        BadRequestException: If the refresh token is invalid or user not found.

    Reference:
        https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
    """
    user = await repos.UserRepo(db).get_by_email(email=user_in.email)

    if user:
        # Generic error message to prevent user enumeration
        raise http_exceptions.BadRequestException(
            detail="Unable to complete registration. Please check your input and try again.",
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
    access_token_data = create_access_token(subject=str(user.id))
    refresh_token_data = create_refresh_token(subject=str(user.id))

    return TokenPairDict(
        access_token=access_token_data["token"],
        refresh_token=refresh_token_data["token"],
    )


async def generate_refresh_token(
    token_payload: TokenPayload,
    db: AsyncSession = Depends(get_session),
) -> TokenPairDict:
    """
    Generate new access and refresh tokens using the provided refresh token.

    Args:
        token_payload: Payload containing the refresh token.
        db: Database session.

    Returns:
        TokenPairDict with new access and refresh tokens.

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
        token_type: str | None = payload.get("type")
        jti: str | None = payload.get("jti")

        if user_id is None:
            raise http_exceptions.UnauthorizedException(
                "Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate token type - must be "refresh" token
        if token_type != "refresh":
            raise http_exceptions.UnauthorizedException(
                "Invalid token type. Expected refresh token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if refresh token is blacklisted
        if jti and await token_blacklist.is_revoked(jti):
            raise http_exceptions.UnauthorizedException(
                "Refresh token has been revoked",
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

    access_token_data = create_access_token(subject=user.id)
    refresh_token_data = create_refresh_token(subject=user.id)

    return TokenPairDict(
        access_token=access_token_data["token"],
        refresh_token=refresh_token_data["token"],
    )


async def login_user_for_access_token(
    user_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_session),
) -> TokenPairDict:
    """
    OAuth2 compatible token login, get an access token for future requests.

    Implements timing attack prevention by always performing password hash
    comparison even when user is not found.

    Args:
        user_data: OAuth2 password request form data
        db: Database session

    Returns:
        TokenPairDict with access and refresh tokens

    Raises:
        UnauthorizedException: If username or password is incorrect

    Reference:
        https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
    """
    user = await repos.UserRepo(db).get_by_username(username=user_data.username)

    # Always perform password verification to prevent timing attacks
    # Use dummy hash if user doesn't exist to ensure constant-time response
    hash_to_verify = user.hashed_password if user else _DUMMY_HASH
    password_valid = verify_password(user_data.password, hash_to_verify)

    if not user or not password_valid:
        raise http_exceptions.UnauthorizedException(
            "Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_data = create_access_token(subject=str(user.id))
    refresh_token_data = create_refresh_token(subject=str(user.id))

    return TokenPairDict(
        access_token=access_token_data["token"],
        refresh_token=refresh_token_data["token"],
    )
