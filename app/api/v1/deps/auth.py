from typing import Annotated

from fastapi import Depends, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app import repos
from app.core.db import get_session
from app.core.exceptions import http_exceptions
from app.models.user import User
from app.schemas import TokenPayload, UserCreate, UserSignup
from app.services.auth_service import AuthService
from app.services.exceptions.auth import (
    DuplicateResourceError,
    ResourceNotFoundError,
    ValidationError,
)
from app.services.types.auth import TokenPairDict

# OAuth2 password bearer scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


def get_auth_service(db: Annotated[AsyncSession, Depends(get_session)]) -> AuthService:
    """Dependency provider for AuthService — the single place AuthService is constructed."""
    return AuthService(user_repo=repos.UserRepo(db))


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """
    Get current authenticated user from JWT token.

    Delegates to AuthService.validate_access_token and translates
    domain exceptions to HTTP exceptions.

    Args:
        token: JWT token
        service: AuthService instance

    Returns:
        Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        return await service.validate_access_token(token)
    except (ValidationError, ResourceNotFoundError) as e:
        raise http_exceptions.UnauthorizedException(
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def generate_access_token(
    user_in: Annotated[UserSignup, Form()],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairDict:
    """
    Register a new user and return access + refresh tokens.

    Delegates to AuthService.register_user and translates
    domain exceptions to HTTP exceptions.

    Args:
        user_in: User signup form data.
        service: AuthService instance.

    Returns:
        TokenPairDict with access and refresh tokens.

    Raises:
        BadRequestException: If registration fails (e.g., duplicate email).
    """
    hashed_password = service.get_password_hash(user_in.password.get_secret_value())
    try:
        return await service.register_user(
            UserCreate(
                first_name="",
                last_name="",
                username=user_in.username,
                email=user_in.email,
                hashed_password=hashed_password,
            )
        )
    except DuplicateResourceError as e:
        raise http_exceptions.BadRequestException(detail=str(e))


async def generate_refresh_token(
    token_payload: TokenPayload,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairDict:
    """
    Generate new access and refresh tokens using the provided refresh token.

    Delegates to AuthService.refresh_tokens and translates
    domain exceptions to HTTP exceptions.

    Args:
        token_payload: Payload containing the refresh token.
        service: AuthService instance.

    Returns:
        TokenPairDict with new access and refresh tokens.

    Raises:
        UnauthorizedException: If the refresh token is invalid or user not found.
    """
    try:
        return await service.refresh_tokens(token_payload.refresh_token)
    except (ValidationError, ResourceNotFoundError) as e:
        raise http_exceptions.UnauthorizedException(
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def login_user_for_access_token(
    user_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairDict:
    """
    OAuth2 compatible token login, get an access token for future requests.

    Delegates to AuthService.authenticate_user and translates
    domain exceptions to HTTP exceptions.

    Args:
        user_data: OAuth2 password request form data
        service: AuthService instance

    Returns:
        TokenPairDict with access and refresh tokens

    Raises:
        UnauthorizedException: If username or password is incorrect
    """
    try:
        return await service.authenticate_user(
            username=user_data.username,
            password=user_data.password,
        )
    except ValidationError as e:
        raise http_exceptions.UnauthorizedException(
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
