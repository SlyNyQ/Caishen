from fastapi import APIRouter

from app.api.routes_chat import router as chat_router
from app.api.routes_health import router as health_router


def build_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(health_router)
    router.include_router(chat_router)
    router.include_router(health_router, prefix="/api")
    router.include_router(chat_router, prefix="/api")
    return router
