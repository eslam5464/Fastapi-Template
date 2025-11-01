import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app import repos
from app.core import exceptions
from app.core.config import settings
from app.core.db import get_session
from app.core.utils import parse_user_id
from app.models.user import User
from app.schemas.token import TokenData

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
    credentials_exception = exceptions.UnauthorizedException(
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    credentials_expired = exceptions.UnauthorizedException(
        detail="Token has expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    credentials_claims_error = exceptions.UnauthorizedException(
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
