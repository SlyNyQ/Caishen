"""Shared helpers for Caishen local and live API evaluation probes."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def build_payload(
    *,
    message: str,
    provider: str = "mock",
    session_id: str = "caishen-eval",
    client_request_id: str | None = None,
    tickers: list[str] | None = None,
    source_urls: list[str] | None = None,
    risk_tolerance: str = "unspecified",
    horizon: str = "unspecified",
    goal: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "message": message,
        "session_id": session_id,
        "provider": provider,
        "analysis_context": {
            "tickers": tickers or [],
            "source_urls": source_urls or [],
            "risk_tolerance": risk_tolerance,
            "horizon": horizon,
            "goal": goal,
        },
    }
    if client_request_id:
        payload["client_request_id"] = client_request_id
    return payload


def request_chat(
    *,
    payload: dict[str, Any],
    api_base_url: str | None = None,
) -> tuple[int, dict[str, Any] | str]:
    if not api_base_url:
        from fastapi.testclient import TestClient

        from app.main import create_app

        with TestClient(create_app()) as client:
            response = client.post("/chat", json=payload)
            try:
                body: dict[str, Any] | str = response.json()
            except ValueError:
                body = response.text
            return response.status_code, body

    request = urllib_request.Request(
        url=f"{api_base_url.rstrip('/')}/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body


def post_chat(*, payload: dict[str, Any], api_base_url: str | None = None) -> dict[str, Any]:
    status, body = request_chat(payload=payload, api_base_url=api_base_url)
    if not 200 <= status < 300 or not isinstance(body, dict):
        raise RuntimeError(f"Chat request failed with {status}: {body}")
    return body


def summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    analysis = payload.get("analysis") or {}
    return {
        "request_id": payload.get("request_id"),
        "route": payload.get("route"),
        "provider": payload.get("provider"),
        "model": payload.get("model"),
        "citation_count": len(payload.get("citations") or []),
        "tool_trace_count": len(payload.get("tool_traces") or []),
        "snapshot_count": len(analysis.get("market_snapshots") or []),
        "source_count": len(analysis.get("source_summaries") or []),
        "refusal_category": (payload.get("refusal") or {}).get("category"),
        "answer_preview": str(payload.get("answer", "")).replace("\n", " ")[:200],
    }


def validate_payload(
    payload: dict[str, Any],
    *,
    expected_route: str | None = None,
    require_citations: bool = False,
    require_tool_traces: bool = False,
    require_refusal: bool = False,
) -> list[str]:
    failures: list[str] = []
    if expected_route and payload.get("route") != expected_route:
        failures.append(f"expected route '{expected_route}', received '{payload.get('route')}'")
    if require_citations and not payload.get("citations"):
        failures.append("expected at least one citation")
    if require_tool_traces and not payload.get("tool_traces"):
        failures.append("expected at least one tool trace")
    if require_refusal and not payload.get("refusal"):
        failures.append("expected a refusal")
    if not isinstance(payload.get("analysis"), dict):
        failures.append("expected structured analysis")
    return failures
