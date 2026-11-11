from .base import BaseRepository

# --- FEATURE[auth] START ---
from .user import UserRepo

# --- FEATURE[auth] END ---

__all__ = [
    "BaseRepository",
    # --- FEATURE[auth] START ---
    "UserRepo",
    # --- FEATURE[auth] END ---
]
