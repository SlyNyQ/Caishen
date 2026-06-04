from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.api.schemas import AnalysisContext
from app.orchestrator.intent_classifier import classify_intent
from app.orchestrator.refusal_classifier import classify_refusal_intent


@dataclass(frozen=True, slots=True)
class RouteDecision:
    route: str
    intent: str
    confidence: float
    allowed: bool
    tickers: tuple[str, ...] = ()
    requires_research_notes: bool = False
    prohibited_reason: str | None = None
    clarification_question: str | None = None

    def to_debug_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "intent": self.intent,
            "confidence": self.confidence,
            "allowed": self.allowed,
            "tickers": list(self.tickers),
            "requires_research_notes": self.requires_research_notes,
            "prohibited_reason": self.prohibited_reason,
            "clarification_question": self.clarification_question,
        }


def route_message(message: str, context: AnalysisContext) -> RouteDecision:
    refusal = classify_refusal_intent(message)
    if not refusal.allowed:
        return RouteDecision(
            route="refusal_route",
            intent=refusal.intent,
            confidence=refusal.confidence,
            allowed=False,
            prohibited_reason=refusal.prohibited_reason,
        )
    intent = classify_intent(message, context)
    return RouteDecision(
        route=intent.route,
        intent=intent.intent,
        confidence=intent.confidence,
        allowed=True,
        tickers=intent.tickers,
        requires_research_notes=intent.requires_research_notes,
        clarification_question=intent.clarification_question,
    )
