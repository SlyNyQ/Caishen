from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    dependencies = request.app.state.dependencies
    return {
        "status": "ok",
        "app": dependencies.settings.app_name,
        "environment": dependencies.settings.app_env,
    }


@router.get("/ready")
async def ready(request: Request) -> dict[str, object]:
    dependencies = request.app.state.dependencies
    return {
        "status": "ready",
        "providers": list(dependencies.settings.configured_providers()),
        "default_provider": dependencies.settings.default_provider,
        "research_notes_loaded": bool(
            dependencies.retriever is not None and dependencies.retriever.chunks
        ),
    }
