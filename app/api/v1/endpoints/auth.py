import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app import repos
from app.core import responses
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
from app.schemas import (
    Token,
    TokenPayload,
    UserCreate,
    UserSignup,
)

router = APIRouter()


@router.post(
    "/login",
    response_model=Token,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": responses.UnauthorizedResponse},
        status.HTTP_400_BAD_REQUEST: {"model": responses.BadRequestResponse},
    },
    summary="Login for access token",
    description="Authenticate user and return access and refresh tokens.",
)
async def login_for_access_token(
    user_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_session),
):
    """
    OAuth2 compatible token login, get an access token for future requests
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
    user_in: Annotated[UserSignup, Form()],
    db: AsyncSession = Depends(get_session),
):
    """
    Create a new user and return an access token
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
    token_payload: TokenPayload,
    db: AsyncSession = Depends(get_session),
):
    """
    Refresh access token using the refresh token
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
