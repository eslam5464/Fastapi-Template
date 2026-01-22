from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from jose import jwt
from jose.exceptions import JWTError
from loguru import logger

from app.api.v1.deps.auth import (
    generate_access_token,
    generate_refresh_token,
    get_current_user,
    login_user_for_access_token,
    oauth2_scheme,
)
from app.core import responses
from app.core.config import settings
from app.core.exceptions import http_exceptions
from app.core.types import TokenPairDict
from app.models.user import User
from app.schemas import (
    LogoutResponse,
    Token,
)
from app.services.cache.token_blacklist import token_blacklist

router = APIRouter()


@router.post(
    "/login",
    response_model=Token,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": responses.UnauthorizedResponse},
    },
    summary="Login for access token",
    description="Authenticate user and return access and refresh tokens.",
)
async def login_for_access_token(
    tokens: Annotated[TokenPairDict, Depends(login_user_for_access_token)],
) -> Token:
    """Login endpoint - validates response with Pydantic Token schema."""
    return Token(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


@router.post(
    "/signup",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": responses.BadRequestResponse},
    },
    summary="User signup",
    description="Create a new user and return access and refresh tokens.",
)
async def signup(
    tokens: Annotated[TokenPairDict, Depends(generate_access_token)],
) -> Token:
    """Signup endpoint - validates response with Pydantic Token schema."""
    return Token(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


@router.post(
    "/refresh-token",
    response_model=Token,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": responses.UnauthorizedResponse},
    },
    summary="Refresh access token",
    description="Refresh access token using the refresh token.",
)
async def refresh_token(
    tokens: Annotated[TokenPairDict, Depends(generate_refresh_token)],
) -> Token:
    """Refresh token endpoint - validates response with Pydantic Token schema."""
    return Token(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": responses.UnauthorizedResponse},
    },
    summary="Logout and revoke token",
    description="Revoke the current access token. After logout, the token cannot be used again.",
)
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LogoutResponse:
    """
    Logout endpoint that revokes the current access token.

    The token is added to a blacklist in Redis with TTL matching
    the remaining token lifetime.

    Reference:
        https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
    """
    try:
        payload = jwt.decode(
            token=token,
            key=settings.secret_key,
            algorithms=settings.jwt_algorithm,
        )

        jti: str | None = payload.get("jti")
        exp: int | None = payload.get("exp")

        if not jti or not exp:
            raise http_exceptions.UnauthorizedException(
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Calculate remaining TTL
        now = int(datetime.now(UTC).timestamp())
        ttl = max(exp - now, 1)  # At least 1 second TTL

        # Add token to blacklist
        await token_blacklist.revoke_token(jti=jti, ttl_seconds=ttl)

        # Return validated Pydantic response
        return LogoutResponse(message="Successfully logged out", revoked=True)
    except JWTError:
        raise http_exceptions.UnauthorizedException(
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Logout failed for user {current_user.id}")
        logger.debug(str(e), exc_info=True)
        raise http_exceptions.InternalServerErrorException(
            detail=f"Logout failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
