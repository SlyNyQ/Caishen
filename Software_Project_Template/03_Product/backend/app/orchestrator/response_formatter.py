from __future__ import annotations

from typing import Any

from app.api.schemas import ChatResponse, Citation, Refusal, ResponseAnalysis, ToolTrace


def format_chat_response(
    *,
    request_id: str,
    session_id: str,
    route: str,
    provider: str,
    model: str,
    answer: str,
    analysis: dict[str, Any] | None = None,
    tool_traces: list[dict[str, Any]] | None = None,
    citations: list[dict[str, Any]] | None = None,
    refusal: dict[str, Any] | None = None,
    debug: dict[str, Any] | None = None,
) -> ChatResponse:
    return ChatResponse(
        request_id=request_id,
        session_id=session_id,
        route=route,
        provider=provider,
        model=model,
        answer=answer,
        analysis=ResponseAnalysis(**(analysis or {})),
        tool_traces=[ToolTrace(**trace) for trace in tool_traces or []],
        citations=[Citation(**citation) for citation in citations or []],
        refusal=Refusal(**refusal) if refusal else None,
        debug=debug or {},
    )
