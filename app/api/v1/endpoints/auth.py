from typing import Annotated

from fastapi import APIRouter, Depends, status
from loguru import logger

from app.api.v1.deps.auth import (
    generate_access_token,
    generate_refresh_token,
    get_auth_service,
    get_current_user,
    login_user_for_access_token,
    oauth2_scheme,
)
from app.core import responses
from app.core.exceptions import http_exceptions
from app.models.user import User
from app.schemas import (
    LogoutResponse,
    Token,
)
from app.services.auth_service import AuthService

# --- FEATURE[redis_token_blacklist] START ---
from app.services.cache.token_blacklist import token_blacklist

# --- FEATURE[redis_token_blacklist] END ---
from app.services.exceptions.auth import ValidationError
from app.services.types.auth import TokenPairDict

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
    summary="Logout",
    description="Log out. When token revocation is enabled, the access token is revoked and cannot be used again.",
)
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LogoutResponse:
    """
    Logout endpoint.

    With token revocation, the access token is added to a blacklist with a TTL
    matching its remaining lifetime and `revoked` is true; without it, `revoked`
    is false and the token stays valid until it expires.

    Reference:
        https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
    """
    try:
        # True once the token is on the blacklist. Without token revocation the
        # token stays valid until it expires.
        revoked = False

        # --- FEATURE[redis_token_blacklist] START ---
        revoke_payload = await auth_service.get_logout_revoke_payload(token)

        # Add token to blacklist
        await token_blacklist.revoke_token(
            jti=revoke_payload["jti"],
            ttl_seconds=revoke_payload["ttl_seconds"],
        )
        revoked = True
        # --- FEATURE[redis_token_blacklist] END ---

        # Return validated Pydantic response
        return LogoutResponse(message="Successfully logged out", revoked=revoked)
    except ValidationError as ex:
        raise http_exceptions.UnauthorizedException(
            detail=str(ex),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except http_exceptions.UnauthorizedException as ex:
        # Re-raise UnauthorizedException without converting to 500
        raise ex
    except Exception:
        logger.exception(f"Logout failed for user {current_user.id}")
        raise http_exceptions.InternalServerErrorException(
            detail="Logout failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
