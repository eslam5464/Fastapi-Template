import uuid


def parse_user_id(user_id: str | int | uuid.UUID) -> str | int | uuid.UUID:
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
