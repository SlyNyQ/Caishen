from __future__ import annotations

from dataclasses import dataclass
import json
import time
import uuid

from app.api.schemas import ChatRequest, ChatResponse
from app.config import Settings
from app.llm.providers import GenerationRequest, ProviderRegistry
from app.orchestrator.analysis_builder import build_analysis
from app.orchestrator.intent_router import route_message
from app.orchestrator.response_formatter import format_chat_response
from app.rag.retriever import KnowledgeRetriever, RetrieverResult
from app.tools.market_data import (
    MarketDataClient,
    MarketDataUnavailable,
    unavailable_snapshot,
)
from app.tools.web_sources import PublicSourceFetcher, unavailable_source


SYSTEM_PROMPT = """You are Caishen, a plain-English investment research assistant.
Explain evidence, uncertainty, risk, and tradeoffs. Use supplied tool results and citations faithfully.
Never claim to execute trades, guarantee outcomes, or issue personalized buy/sell directives.
Clearly distinguish current market data, public-source context, and general educational explanation."""


def _build_prompt(
    request: ChatRequest,
    *,
    route: str,
    tool_traces: list[dict[str, object]],
    citations: list[dict[str, object]],
) -> str:
    payload = {
        "user_request": request.message,
        "route": route,
        "analysis_context": request.analysis_context.model_dump(),
        "tool_results": tool_traces,
        "research_citations": citations,
        "response_requirements": [
            "Use plain English.",
            "State important uncertainty and data freshness limitations.",
            "Offer educational scenarios, not personalized trade instructions.",
            "Do not invent missing market values or source claims.",
        ],
    }
    return json.dumps(payload, indent=2, default=str)


@dataclass(slots=True)
class WorkflowEngine:
    settings: Settings
    provider_registry: ProviderRegistry
    market_data: MarketDataClient
    source_fetcher: PublicSourceFetcher
    retriever: KnowledgeRetriever | None = None

    def handle_chat(self, request: ChatRequest) -> ChatResponse:
        request_id = request.client_request_id or f"req-{uuid.uuid4().hex[:12]}"
        session_id = request.session_id or f"session-{uuid.uuid4().hex[:12]}"
        started_at = time.perf_counter()
        provider, model = self.provider_registry.resolve(request.provider, request.model)
        decision = route_message(request.message, request.analysis_context)

        if not decision.allowed:
            answer = (
                f"{decision.prohibited_reason} "
                "I can still explain relevant market concepts, evidence, risks, and educational scenarios."
            )
            return format_chat_response(
                request_id=request_id,
                session_id=session_id,
                route=decision.route,
                provider=provider,
                model=model,
                answer=answer,
                refusal={"category": decision.intent, "message": answer},
                analysis={
                    "risk_notes": [
                        "Caishen is an educational, read-only research assistant and cannot execute trades."
                    ]
                },
                debug=self._debug(decision.to_debug_dict(), started_at),
            )

        if decision.route == "clarification_route":
            return format_chat_response(
                request_id=request_id,
                session_id=session_id,
                route=decision.route,
                provider=provider,
                model=model,
                answer=decision.clarification_question or "What investment topic would you like to explore?",
                debug=self._debug(decision.to_debug_dict(), started_at),
            )

        tool_traces: list[dict[str, object]] = []
        snapshots: list[dict[str, object]] = []
        for ticker in decision.tickers:
            try:
                snapshot = self.market_data.get_snapshot(ticker)
                warnings = ["Market data may be delayed; verify before relying on it."]
            except MarketDataUnavailable as exc:
                snapshot = unavailable_snapshot(ticker, str(exc))
                warnings = [str(exc)]
            snapshots.append(snapshot)
            tool_traces.append(
                {
                    "name": "market_snapshot",
                    "arguments": {"ticker": ticker},
                    "result": snapshot,
                    "warnings": warnings,
                }
            )

        sources: list[dict[str, str]] = []
        citations: list[dict[str, object]] = []
        for index, url in enumerate(request.analysis_context.source_urls):
            try:
                source = self.source_fetcher.fetch(url)
                warnings: list[str] = []
            except Exception as exc:
                source = unavailable_source(url, f"Public source unavailable: {exc}")
                warnings = [str(exc)]
            sources.append(source)
            tool_traces.append(
                {
                    "name": "public_source_summary",
                    "arguments": {"url": url},
                    "result": source,
                    "warnings": warnings,
                }
            )
            if source["status"] == "available":
                citations.append(
                    {
                        "doc_id": f"public_source_{index + 1}",
                        "title": source["title"],
                        "snippet": source["summary"][:280],
                        "score": 1.0,
                        "metadata": {"source_url": source["url"], "fetched_at": source["fetched_at"]},
                    }
                )

        retrieval_result = RetrieverResult.empty(reason="retrieval_not_requested")
        if decision.requires_research_notes and self.retriever is not None:
            retrieval_result = self.retriever.retrieve(request.message)
            if retrieval_result.usable_context:
                citations.extend(retrieval_result.citations)

        analysis = build_analysis(
            context=request.analysis_context,
            market_snapshots=snapshots,
            source_summaries=sources,
        )
        prompt = _build_prompt(
            request,
            route=decision.route,
            tool_traces=tool_traces,
            citations=citations,
        )
        generation = self.provider_registry.generate(
            GenerationRequest(
                route=decision.route,
                user_message=request.message,
                system_prompt=SYSTEM_PROMPT,
                prompt=prompt,
                tool_results=tool_traces,
                citations=citations,
            ),
            provider=provider,
            model=model,
        )
        debug = self._debug(
            {
                **decision.to_debug_dict(),
                "llm_request_id": generation.request_id,
                "usage": generation.usage,
                "retrieval_reason": retrieval_result.fallback_reason,
                "retrieved_count": retrieval_result.retrieved_count,
            },
            started_at,
        )
        return format_chat_response(
            request_id=request_id,
            session_id=session_id,
            route=decision.route,
            provider=generation.provider,
            model=generation.model,
            answer=generation.text,
            analysis=analysis,
            tool_traces=tool_traces,
            citations=citations,
            debug=debug,
        )

    def _debug(self, payload: dict[str, object], started_at: float) -> dict[str, object]:
        if not self.settings.enable_debug_traces:
            return {}
        return {
            **payload,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 3),
        }
