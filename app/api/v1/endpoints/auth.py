from fastapi import APIRouter, Depends, status

from app.api.v1.deps.auth import (
    generate_access_token,
    generate_refresh_token,
    login_user_for_access_token,
)
from app.core import responses
from app.schemas import (
    Token,
)

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
    tokens: dict[str, str] = Depends(login_user_for_access_token),
):
    return tokens


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
    tokens: dict[str, str] = Depends(generate_access_token),
):
    return tokens


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
    tokens: dict[str, str] = Depends(generate_refresh_token),
):
    return tokens
