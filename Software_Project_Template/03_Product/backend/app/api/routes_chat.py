from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.schemas import ChatRequest, ChatResponse
from app.errors import to_http_exception


router = APIRouter(tags=["analysis"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    try:
        return request.app.state.dependencies.workflow_engine.handle_chat(payload)
    except Exception as exc:  # pragma: no cover - integration-tested translation
        raise to_http_exception(exc) from exc
