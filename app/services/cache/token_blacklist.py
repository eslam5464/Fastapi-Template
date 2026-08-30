import time

from loguru import logger
from redis.asyncio import Redis

from app.core.config import Environment, settings
from app.services.cache import BaseRedisClient


class TokenBlacklist(BaseRedisClient):
    """
    Token blacklist service for JWT revocation.

    Stores revoked token JTIs in Redis with automatic expiration.
    This allows for immediate token invalidation (e.g., on logout)
    while tokens are still within their expiration window.

    Redis-based token revocation for JWT tokens.
    Stores revoked token JTIs (JWT IDs) with TTL matching token expiration.

    Reference: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
    """

    # Key prefix for blacklisted tokens
    KEY_PREFIX = "token:blacklist:"

    async def revoke_token(self, jti: str, ttl_seconds: int) -> bool:
        """
        Revoke a token by adding its JTI to the blacklist.

        Args:
            jti: The JWT ID (jti claim) of the token to revoke
            ttl_seconds: Time-to-live in seconds (should match remaining token lifetime)

        Returns:
            bool: True if successfully blacklisted, False otherwise
        """
        # Skip in local environment where Redis is not available
        if settings.current_environment == Environment.LOCAL:
            logger.debug(f"Token blacklist skipped in LOCAL environment: {jti}")
            return True

        async def _revoke(client: Redis) -> bool:
            key = f"{self.KEY_PREFIX}{jti}"
            # Store with expiration matching token TTL
            await client.setex(key, ttl_seconds, "revoked")
            logger.info(f"Token revoked: {jti[:8]}... (TTL: {ttl_seconds}s)")
            return True

        return await self._safe_call(_revoke, default=False, context=f"Token revoke for {jti[:8]}...")

    async def is_revoked(self, jti: str) -> bool:
        """
        Check if a token has been revoked.

        Args:
            jti: The JWT ID (jti claim) to check

        Returns:
            bool: True if token is revoked, False otherwise
        """
        # Skip in local environment - tokens are not revoked
        if settings.current_environment == Environment.LOCAL:
            return False

        async def _is_revoked(client: Redis) -> bool:
            key = f"{self.KEY_PREFIX}{jti}"
            return bool(await client.exists(key) > 0)

        # Fail open (not revoked) if Redis is unavailable or the check errors — see
        # BaseRedisClient._safe_call. In high-security environments, fail closed instead.
        return await self._safe_call(_is_revoked, default=False, context=f"Token revocation check for {jti[:8]}...")

    async def revoke_all_user_tokens(self, user_id: str, ttl_seconds: int) -> bool:
        """
        Revoke all tokens for a specific user (for password change, account compromise, etc.)

        This is a marker-based approach - stores user ID with timestamp.
        Token validation should check if token was issued before revocation time.

        Args:
            user_id: The user ID whose tokens should be revoked
            ttl_seconds: Time-to-live in seconds

        Returns:
            bool: True if successfully stored, False otherwise
        """
        if settings.current_environment == Environment.LOCAL:
            return True

        async def _revoke_all(client: Redis) -> bool:
            key = f"token:revoke_all:{user_id}"
            # Store the timestamp when all tokens were revoked
            await client.setex(key, ttl_seconds, str(int(time.time())))
            logger.info(f"All tokens revoked for user: {user_id}")
            return True

        return await self._safe_call(_revoke_all, default=False, context=f"Revoke-all-tokens for user {user_id}")

    async def get_user_revocation_time(self, user_id: str) -> int | None:
        """
        Get the timestamp when all tokens were revoked for a user.

        Args:
            user_id: The user ID to check

        Returns:
            int | None: Unix timestamp of revocation, or None if not revoked
        """
        if settings.current_environment == Environment.LOCAL:
            return None

        async def _get_revocation_time(client: Redis) -> int | None:
            key = f"token:revoke_all:{user_id}"
            value = await client.get(key)
            return int(value) if value else None

        return await self._safe_call(
            _get_revocation_time,
            default=None,
            context=f"Revocation-time lookup for user {user_id}",
        )


# Global token blacklist instance
token_blacklist = TokenBlacklist()
