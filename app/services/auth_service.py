import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional, cast

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError
from pwdlib import PasswordHash

from app.core.config import settings
from app.models.user import User
from app.repos.user import UserRepo
from app.schemas import TokenData, UserCreate
from app.services.cache.token_blacklist import token_blacklist
from app.services.exceptions.auth import (
    DuplicateResourceError,
    ResourceNotFoundError,
    ValidationError,
)
from app.services.types.auth import (
    JWTPayloadDict,
    LogoutRevokePayloadDict,
    TokenPairDict,
    TokenWithJtiDict,
)


class AuthService:
    """
    Authentication service handling user registration, login, and token management.
    Receives UserRepo via constructor — never sees database sessions.

    Raises service exceptions (ValidationError, ResourceNotFoundError, DuplicateResourceError)
    which are caught and translated to HTTP exceptions by the deps layer.
    """

    def __init__(
        self,
        user_repo: UserRepo,
        dummy_hash: str | None = None,
        password_hash: PasswordHash | None = None,
    ):
        self.user_repo = user_repo
        self._password_hash = password_hash or PasswordHash.recommended()

        # Pre-computed dummy hash for timing attack prevention
        # Reference: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
        self._dummy_hash = dummy_hash or self._password_hash.hash(
            "dummy_password_for_timing_attack_prevention"
        )

    @staticmethod
    def generate_random_password(length: int = 12) -> str:
        """
        Generate a random password using letters, digits, and punctuation.

        Args:
            length (int): Desired length of the generated password. Default is 12.

        Returns:
            str: A randomly generated password string.

        Raises:
            ValueError: If the specified length is less than 8 characters.
        """
        if length < 8:
            raise ValueError("Password length must be at least 8 characters")

        alphabet = string.ascii_letters + string.digits + string.punctuation
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def create_access_token(
        subject: str | int | uuid.UUID,
        expires_delta: Optional[timedelta] = None,
    ) -> TokenWithJtiDict:
        """
        Create JWT access token with type and JTI claims.

        Args:
            subject (str | int | uuid.UUID): The subject claim for the token (usually user ID).
            expires_delta (Optional[timedelta]): Optional custom expiration time for the token.

        Returns:
            TokenWithJtiDict: A dictionary containing the encoded JWT token and its JTI.

        Raises:
            JWTError: If there is an error encoding the JWT token.
        """
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(seconds=settings.access_token_expire_seconds)

        jti = str(uuid.uuid4())
        to_encode: JWTPayloadDict = {
            "exp": int(expire.timestamp()),
            "sub": str(subject),
            "iat": int(datetime.now(UTC).timestamp()),
            "type": "access",
            "jti": jti,
        }
        encoded_jwt = jwt.encode(
            dict(to_encode), settings.secret_key, algorithm=settings.jwt_algorithm
        )
        return TokenWithJtiDict(token=encoded_jwt, jti=jti)

    @staticmethod
    def create_refresh_token(subject: str | int | uuid.UUID) -> TokenWithJtiDict:
        """
        Create JWT refresh token with type and JTI claims.

        Args:
            subject (str | int | uuid.UUID): The subject claim for the token (usually user ID).

        Returns:
            TokenWithJtiDict: A dictionary containing the encoded JWT token and its JTI.

        Raises:
            JWTError: If there is an error encoding the JWT token.
        """
        expire = datetime.now(UTC) + timedelta(seconds=settings.refresh_token_expire_seconds)
        jti = str(uuid.uuid4())
        to_encode: JWTPayloadDict = {
            "exp": int(expire.timestamp()),
            "sub": str(subject),
            "iat": int(datetime.now(UTC).timestamp()),
            "type": "refresh",
            "jti": jti,
        }
        encoded_jwt = jwt.encode(
            dict(to_encode), settings.secret_key, algorithm=settings.jwt_algorithm
        )

        return TokenWithJtiDict(token=encoded_jwt, jti=jti)

    @staticmethod
    def _decode_jwt_payload(
        token: str,
        expired_error_message: str,
        invalid_error_message: str,
        claims_error_message: str | None = None,
    ) -> JWTPayloadDict:
        """
        Decode JWT and normalize decode errors into ValidationError.

        Args:
            token: JWT token string to decode.
            expired_error_message: Error message for expired token.
            invalid_error_message: Error message for invalid token.
            claims_error_message: Optional error message for claims validation.

        Returns:
            JWTPayloadDict: Decoded JWT payload.

        Raises:
            ValidationError: If the token is expired, invalid, or has invalid claims.
        """
        try:
            payload = jwt.decode(
                token=token,
                key=settings.secret_key,
                algorithms=settings.jwt_algorithm,
            )
            return cast(JWTPayloadDict, payload)
        except ExpiredSignatureError:
            raise ValidationError(expired_error_message)
        except JWTClaimsError:
            raise ValidationError(claims_error_message or invalid_error_message)
        except JWTError:
            raise ValidationError(invalid_error_message)

    @staticmethod
    def _parse_user_id(user_id: str | int | uuid.UUID) -> str | int | uuid.UUID:
        """
        Parse user_id to appropriate type

        Args:
            user_id (str | int | uuid.UUID): The user ID to parse

        Returns:
            user_id (str | int | uuid.UUID): Parsed user ID
        """
        if isinstance(user_id, uuid.UUID):
            return user_id

        try:
            return uuid.UUID(str(user_id))
        except ValueError:
            pass

        try:
            return int(user_id)
        except (ValueError, TypeError):
            pass

        return user_id

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """

        Verify password against hashed password.

        Args:
            plain_password: The plaintext password to verify.
            hashed_password: The hashed password to compare against.

        Returns:
            bool: True if the password is correct, False otherwise.

        Raises:
            pwdlib.exceptions.UnknownHashError: If the hash algorithm is unknown.
        """
        return self._password_hash.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Hash plain password for storage.

        Args:
            password: The plaintext password to hash.

        Returns:
            str: The hashed password.
        """
        return self._password_hash.hash(password)

    async def get_logout_revoke_payload(self, token: str) -> LogoutRevokePayloadDict:
        """
        Decode token and return blacklist revoke data as a typed payload.

        Args:
            token: The JWT token to decode.

        Returns:
            LogoutRevokePayloadDict: The payload containing the jti and ttl_seconds.

        Raises:
            ValidationError: If the token is invalid or expired.
        """
        payload = self._decode_jwt_payload(
            token=token,
            expired_error_message="Token has expired",
            invalid_error_message="Invalid token",
        )

        jti: str | None = payload.get("jti")
        expires_at: int | None = payload.get("exp")

        if not jti or not expires_at:
            raise ValidationError("Invalid token format")

        now = int(datetime.now(UTC).timestamp())
        return LogoutRevokePayloadDict(jti=jti, ttl_seconds=max(expires_at - now, 1))

    async def register_user(self, signup_data: UserCreate) -> TokenPairDict:
        """
        Register a new user and return token pair.

        Args:
            signup_data: UserCreate schema with registration data.

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

        user = await self.user_repo.create_one(
            schema=signup_data,
        )

        access_token_data = self.create_access_token(subject=str(user.id))
        refresh_token_data = self.create_refresh_token(subject=str(user.id))

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
        hash_to_verify = user.hashed_password if user else self._dummy_hash
        password_valid = self.verify_password(password, hash_to_verify)

        if not user or not password_valid:
            raise ValidationError("Incorrect username or password")

        access_token_data = self.create_access_token(subject=str(user.id))
        refresh_token_data = self.create_refresh_token(subject=str(user.id))

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
        payload = self._decode_jwt_payload(
            token=token,
            expired_error_message="Token has expired",
            invalid_error_message="Could not validate credentials",
            claims_error_message="Token has invalid claims",
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

        try:
            token_data = TokenData(
                user_id=self._parse_user_id(user_id),
                issued_at=issued_at,
                expires_at=expires_at,
            )
        except (TypeError, ValueError, JWTClaimsError):
            raise ValidationError("Token has invalid claims")

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
        payload = self._decode_jwt_payload(
            token=refresh_token,
            expired_error_message="Refresh token has expired",
            invalid_error_message="Invalid refresh token",
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

        try:
            user_id = self._parse_user_id(user_id)
        except (TypeError, ValueError):
            raise ValidationError("Invalid refresh token")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("Invalid user")

        access_token_data = self.create_access_token(subject=user.id)
        refresh_token_data = self.create_refresh_token(subject=user.id)

        return TokenPairDict(
            access_token=access_token_data["token"],
            refresh_token=refresh_token_data["token"],
        )
