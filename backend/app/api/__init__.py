from fastapi import APIRouter

from . import admin, auth, timers

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(timers.router, prefix="/timers", tags=["timers"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

__all__ = ["api_router"]
