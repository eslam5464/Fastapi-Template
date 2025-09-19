from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps.auth import get_current_user
from app.core import responses
from app.models import User
from app.schemas import UserResponse

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": responses.UnauthorizedResponse},
    },
    summary="Read current user",
)
async def read_user_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
