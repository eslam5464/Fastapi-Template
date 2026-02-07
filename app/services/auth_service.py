import uuid

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.core.config import settings
from app.core.exceptions.domain import (
    DuplicateResourceError,
    ResourceNotFoundError,
    ValidationError,
)
from app.core.types import TokenPairDict
from app.core.utils import parse_user_id
from app.models.user import User
from app.repos.user import UserRepo
from app.schemas import TokenData, UserCreate, UserSignup
from app.services.cache.token_blacklist import token_blacklist

# Pre-computed dummy hash for timing attack prevention
# Reference: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
_DUMMY_HASH = get_password_hash("dummy_password_for_timing_attack_prevention")


class AuthService:
    """
    Authentication service handling user registration, login, and token management.
    Receives UserRepo via constructor — never sees database sessions.

    Raises domain exceptions (ValidationError, ResourceNotFoundError, DuplicateResourceError)
    which are caught and translated to HTTP exceptions by the deps layer.
    """

    def __init__(self, user_repo: UserRepo):
        self.user_repo = user_repo

    async def register_user(self, signup_data: UserSignup) -> TokenPairDict:
        """
        Register a new user and return token pair.

        Args:
            signup_data: User signup data (username, email, password).

        Returns:
            TokenPairDict with access and refresh tokens.

        Raises:
            DuplicateResourceError: If a user with the email already exists.

        Reference:
            https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
        """
        existing = await self.user_repo.get_by_email(email=signup_data.email)
        if existing:
            # Generic message to prevent user enumeration
            raise DuplicateResourceError(
                "Unable to complete registration. Please check your input and try again."
            )

        hashed_password = get_password_hash(signup_data.password.get_secret_value())
        user = await self.user_repo.create_one(
            schema=UserCreate(
                first_name="",
                last_name="",
                username=signup_data.username,
                email=signup_data.email,
                hashed_password=hashed_password,
            ),
        )

        access_token_data = create_access_token(subject=str(user.id))
        refresh_token_data = create_refresh_token(subject=str(user.id))

        return TokenPairDict(
            access_token=access_token_data["token"],
            refresh_token=refresh_token_data["token"],
        )

    async def authenticate_user(self, username: str, password: str) -> TokenPairDict:
        """
        Authenticate user by username and password, return token pair.

        Implements timing attack prevention by always performing password hash
        comparison even when user is not found.

        Args:
            username: User's username.
            password: User's password (plaintext).

        Returns:
            TokenPairDict with access and refresh tokens.

        Raises:
            ValidationError: If username or password is incorrect.

        Reference:
            https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
        """
        user = await self.user_repo.get_by_username(username=username)

        # Always perform password verification to prevent timing attacks
        # Use dummy hash if user doesn't exist to ensure constant-time response
        hash_to_verify = user.hashed_password if user else _DUMMY_HASH
        password_valid = verify_password(password, hash_to_verify)

        if not user or not password_valid:
            raise ValidationError("Incorrect username or password")

        access_token_data = create_access_token(subject=str(user.id))
        refresh_token_data = create_refresh_token(subject=str(user.id))

        return TokenPairDict(
            access_token=access_token_data["token"],
            refresh_token=refresh_token_data["token"],
        )

    async def validate_access_token(self, token: str) -> User:
        """
        Validate an access token and return the authenticated user.

        Validates:
        - Token signature and expiration
        - Token type is "access" (not refresh token)
        - Token is not revoked (blacklisted)
        - User exists in database

        Args:
            token: JWT access token string.

        Returns:
            The authenticated User model instance.

        Raises:
            ValidationError: If token is invalid, expired, revoked, or user not found.

        Reference:
            https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
        """
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
                raise ValidationError("Could not validate credentials")

            if token_type != "access":
                raise ValidationError("Token has invalid claims")

            if jti and await token_blacklist.is_revoked(jti):
                raise ValidationError("Token has been revoked")

            token_data = TokenData(
                user_id=parse_user_id(user_id),
                issued_at=issued_at,
                expires_at=expires_at,
            )

        except ExpiredSignatureError:
            raise ValidationError("Token has expired")
        except JWTClaimsError:
            raise ValidationError("Token has invalid claims")
        except JWTError:
            raise ValidationError("Could not validate credentials")

        # Check if all user tokens were revoked (e.g., password change)
        revocation_time = await token_blacklist.get_user_revocation_time(str(token_data.user_id))
        if revocation_time and issued_at and issued_at < revocation_time:
            raise ValidationError("Token has been revoked")

        user = await self.user_repo.get_by_id(token_data.user_id)
        if user is None:
            raise ResourceNotFoundError("User not found")

        return user

    async def refresh_tokens(self, refresh_token: str) -> TokenPairDict:
        """
        Generate new access and refresh tokens using a valid refresh token.

        Args:
            refresh_token: JWT refresh token string.

        Returns:
            TokenPairDict with new access and refresh tokens.

        Raises:
            ValidationError: If the refresh token is invalid, expired, or revoked.
            ResourceNotFoundError: If the user associated with the token no longer exists.
        """
        try:
            payload = jwt.decode(
                refresh_token,
                settings.secret_key,
                algorithms=settings.jwt_algorithm,
            )
            user_id: str | int | uuid.UUID | None = payload.get("sub")
            token_type: str | None = payload.get("type")
            jti: str | None = payload.get("jti")

            if user_id is None:
                raise ValidationError("Invalid refresh token")

            if token_type != "refresh":
                raise ValidationError("Invalid token type. Expected refresh token.")

            if jti and await token_blacklist.is_revoked(jti):
                raise ValidationError("Refresh token has been revoked")

            user_id = parse_user_id(user_id)

        except ExpiredSignatureError:
            raise ValidationError("Refresh token has expired")
        except JWTError:
            raise ValidationError("Invalid refresh token")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("Invalid user")

        access_token_data = create_access_token(subject=user.id)
        refresh_token_data = create_refresh_token(subject=user.id)

        return TokenPairDict(
            access_token=access_token_data["token"],
            refresh_token=refresh_token_data["token"],
        )
