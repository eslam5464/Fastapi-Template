import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from jose import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.types import JWTPayloadDict, TokenWithJtiDict

password_hash = PasswordHash.recommended()


def create_access_token(
    subject: str | int | uuid.UUID,
    expires_delta: Optional[timedelta] = None,
) -> TokenWithJtiDict:
    """
    Create JWT access token with type and JTI claims.

    Args:
        subject: Token subject (usually user ID or username)
        expires_delta: Token expiration time

    Returns:
        TokenWithJtiDict containing the encoded JWT token and JTI

    Reference:
        https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(seconds=settings.access_token_expire_seconds)

    jti = str(uuid.uuid4())  # Unique token identifier for revocation
    to_encode: JWTPayloadDict = {
        "exp": int(expire.timestamp()),  # JWT RFC 7519: NumericDate in seconds
        "sub": str(subject),
        "iat": int(datetime.now(UTC).timestamp()),
        "type": "access",  # Token type to distinguish from refresh tokens
        "jti": jti,  # JWT ID for token revocation
    }
    encoded_jwt = jwt.encode(dict(to_encode), settings.secret_key, algorithm=settings.jwt_algorithm)
    return TokenWithJtiDict(token=encoded_jwt, jti=jti)


def create_refresh_token(subject: str | int | uuid.UUID) -> TokenWithJtiDict:
    """
    Create JWT refresh token with longer expiration and type/JTI claims.

    Args:
        subject: Token subject (usually user ID or username)

    Returns:
        TokenWithJtiDict containing the encoded JWT refresh token and JTI

    Reference:
        https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
    """
    expire = datetime.now(UTC) + timedelta(seconds=settings.refresh_token_expire_seconds)
    jti = str(uuid.uuid4())  # Unique token identifier for revocation
    to_encode: JWTPayloadDict = {
        "exp": int(expire.timestamp()),  # JWT RFC 7519: NumericDate in seconds
        "sub": str(subject),
        "iat": int(datetime.now(UTC).timestamp()),
        "type": "refresh",  # Token type to distinguish from access tokens
        "jti": jti,  # JWT ID for token revocation
    }
    encoded_jwt = jwt.encode(dict(to_encode), settings.secret_key, algorithm=settings.jwt_algorithm)

    return TokenWithJtiDict(token=encoded_jwt, jti=jti)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hashed password
    Args:
        plain_password: Plain password
        hashed_password: Hashed password

    Returns:
        Whether password matches hash
    """
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash password
    Args:
        password: Plain password

    Returns:
        Hashed password
    """
    return password_hash.hash(password)


def generate_random_password(length: int = 12) -> str:
    """
    Generate a random password of specified length
    Args:
        length: Length of the password

    Returns:
        Randomly generated password
    """
    if length < 8:
        raise ValueError("Password length must be at least 8 characters")

    alphabet = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(alphabet) for _ in range(length))
