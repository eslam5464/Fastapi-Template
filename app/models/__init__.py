from app.models.base import Base

# --- FEATURE[auth] START ---
from app.models.user import User

# --- FEATURE[auth] END ---

__all__ = [
    "Base",
    # --- FEATURE[auth] START ---
    "User",
    # --- FEATURE[auth] END ---
]
