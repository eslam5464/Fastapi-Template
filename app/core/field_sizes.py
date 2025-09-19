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
