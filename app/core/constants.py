class RateLimitPrefix:
    """
    Centralized registry of all rate limit key prefixes.

    All rate limit keys follow the pattern: ratelimit:{category}:{identifier}
    where identifier is typically an IP address or user ID.

    Example:
        ```python
        from app.core.constants import RateLimitPrefix

        # Use in rate limiting
        key = f"{RateLimitPrefix.AUTH}{ip_address}"
        # Result: "ratelimit:auth:192.168.1.1"
        ```
    """

    # Authentication endpoints (login, signup, password reset)
    AUTH = "ratelimit:auth:"

    # Authenticated user endpoints (profile, settings, user data)
    USER = "ratelimit:user:"

    # General API endpoints (moderate limits)
    API = "ratelimit:api:"

    # Public endpoints (lenient limits for read-only operations)
    PUBLIC = "ratelimit:public:"

    # Custom endpoint-specific prefixes (add as needed)
    EXPORT = "ratelimit:export:"  # File export operations
    UPLOAD = "ratelimit:upload:"  # File upload operations
    SEARCH = "ratelimit:search:"  # Search queries
    ADMIN = "ratelimit:admin:"  # Admin operations

    @classmethod
    def all_prefixes(cls) -> set[str]:
        """
        Get all registered prefixes for validation.

        Returns:
            set[str]: Set of all registered rate limit prefixes

        Example:
            ```python
            prefixes = RateLimitPrefix.all_prefixes()
            # {'ratelimit:auth:', 'ratelimit:user:', ...}
            ```
        """
        return {
            value
            for key, value in cls.__dict__.items()
            if isinstance(value, str) and value.startswith("ratelimit:")
        }

    @classmethod
    def validate_prefix(cls, prefix: str) -> None:
        """
        Validate that a prefix doesn't conflict with existing ones.

        Args:
            prefix: The prefix to validate (should include "ratelimit:" and trailing ":")

        Raises:
            ValueError: If prefix already exists in the registry

        Example:
            ```python
            # This will raise ValueError if prefix already exists
            RateLimitPrefix.validate_prefix("ratelimit:custom:")
            ```
        """
        if prefix in cls.all_prefixes():
            raise ValueError(
                f"Rate limit prefix '{prefix}' is already registered. "
                f"Existing prefixes: {cls.all_prefixes()}"
            )


class FieldSizes:
    # Common string lengths
    TINY = 20
    SHORT = 50
    MEDIUM = 255
    LONG = 1000
    VERY_LONG = 2000
    EXTRA_LONG = 5000

    # Specific field sizes
    EMAIL = MEDIUM
    USERNAME = MEDIUM
    PASSWORD = SHORT
    PASSWORD_HASH = LONG
    FIRST_NAME = SHORT
    LAST_NAME = SHORT
