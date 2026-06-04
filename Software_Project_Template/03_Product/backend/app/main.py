from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import build_api_router
from app.config import Settings
from app.dependencies import AppDependencies, build_dependencies
from app.env import load_local_env
from app.telemetry.logging import configure_logging


def create_app(
    settings: Settings | None = None,
    *,
    dependencies: AppDependencies | None = None,
) -> FastAPI:
    load_local_env()
    resolved_settings = settings or (dependencies.settings if dependencies else Settings.from_env())
    configure_logging(resolved_settings.log_level)
    resolved_dependencies = dependencies or build_dependencies(resolved_settings)

    app = FastAPI(
        title="Caishen Investment Analysis API",
        description="Read-only market research and educational investment analysis.",
        version="1.0.0",
        debug=resolved_settings.debug,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.dependencies = resolved_dependencies
    app.include_router(build_api_router())
    return app


app = create_app()
