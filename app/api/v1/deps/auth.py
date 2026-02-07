from typing import Annotated

from fastapi import Depends, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app import repos
from app.core.db import get_session
from app.core.exceptions import http_exceptions
from app.core.exceptions.domain import (
    DuplicateResourceError,
    ResourceNotFoundError,
    ValidationError,
)
from app.core.types import TokenPairDict
from app.models.user import User
from app.schemas import TokenPayload, UserSignup
from app.services.auth_service import AuthService

# OAuth2 password bearer scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _get_auth_service(db: AsyncSession) -> AuthService:
    """Create AuthService with UserRepo injected."""
    return AuthService(user_repo=repos.UserRepo(db))


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """
    Get current authenticated user from JWT token.

    Delegates to AuthService.validate_access_token and translates
    domain exceptions to HTTP exceptions.

    Args:
        token: JWT token
        db: Database session

    Returns:
        Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    service = _get_auth_service(db)
    try:
        return await service.validate_access_token(token)
    except (ValidationError, ResourceNotFoundError) as e:
        raise http_exceptions.UnauthorizedException(
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def generate_access_token(
    user_in: Annotated[UserSignup, Form()],
    db: AsyncSession = Depends(get_session),
) -> TokenPairDict:
    """
    Register a new user and return access + refresh tokens.

    Delegates to AuthService.register_user and translates
    domain exceptions to HTTP exceptions.

    Args:
        user_in: User signup form data.
        db: Database session.

    Returns:
        TokenPairDict with access and refresh tokens.

    Raises:
        BadRequestException: If registration fails (e.g., duplicate email).
    """
    service = _get_auth_service(db)
    try:
        return await service.register_user(user_in)
    except DuplicateResourceError as e:
        raise http_exceptions.BadRequestException(detail=str(e))


async def generate_refresh_token(
    token_payload: TokenPayload,
    db: AsyncSession = Depends(get_session),
) -> TokenPairDict:
    """
    Generate new access and refresh tokens using the provided refresh token.

    Delegates to AuthService.refresh_tokens and translates
    domain exceptions to HTTP exceptions.

    Args:
        token_payload: Payload containing the refresh token.
        db: Database session.

    Returns:
        TokenPairDict with new access and refresh tokens.

    Raises:
        UnauthorizedException: If the refresh token is invalid or user not found.
    """
    service = _get_auth_service(db)
    try:
        return await service.refresh_tokens(token_payload.refresh_token)
    except (ValidationError, ResourceNotFoundError) as e:
        raise http_exceptions.UnauthorizedException(
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def login_user_for_access_token(
    user_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_session),
) -> TokenPairDict:
    """
    OAuth2 compatible token login, get an access token for future requests.

    Delegates to AuthService.authenticate_user and translates
    domain exceptions to HTTP exceptions.

    Args:
        user_data: OAuth2 password request form data
        db: Database session

    Returns:
        TokenPairDict with access and refresh tokens

    Raises:
        UnauthorizedException: If username or password is incorrect
    """
    service = _get_auth_service(db)
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
