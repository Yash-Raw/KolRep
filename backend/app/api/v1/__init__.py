from fastapi import APIRouter
from app.api.v1.generations import router as generations_router
from app.api.v1.health import router as health_router
from app.api.v1.storage import router as storage_router
from app.api.v1.usage import router as usage_router
from app.api.v1.verification import router as verification_router
from app.api.v1.voices import router as voices_router
from app.desktop.router import router as desktop_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(voices_router)
api_v1_router.include_router(generations_router)
api_v1_router.include_router(usage_router)
api_v1_router.include_router(storage_router)
api_v1_router.include_router(verification_router)
api_v1_router.include_router(desktop_router)

__all__ = ["api_v1_router"]
