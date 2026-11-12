from fastapi import APIRouter

# --- FEATURE[auth] START ---
from app.api.v1.endpoints.auth import router as auth_router

# --- FEATURE[auth] END ---
# --- FEATURE[example_items] START ---
from app.api.v1.endpoints.items import router as items_router

# --- FEATURE[example_items] END ---
# --- FEATURE[auth] START ---
from app.api.v1.endpoints.user import router as user_router

# --- FEATURE[auth] END ---

api_v1_router = APIRouter()

# --- FEATURE[auth] START ---
api_v1_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_v1_router.include_router(user_router, prefix="/users", tags=["Users"])
# --- FEATURE[auth] END ---
# --- FEATURE[example_items] START ---
api_v1_router.include_router(items_router, prefix="/items", tags=["Items"])
# --- FEATURE[example_items] END ---
