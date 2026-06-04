from __future__ import annotations

from dataclasses import dataclass

from app.api.schemas import AnalysisContext
from app.tools.market_data import extract_tickers


@dataclass(frozen=True, slots=True)
class IntentClassification:
    route: str
    intent: str
    confidence: float
    tickers: tuple[str, ...] = ()
    requires_research_notes: bool = False
    clarification_question: str | None = None


def classify_intent(message: str, context: AnalysisContext) -> IntentClassification:
    lowered = " ".join(message.strip().lower().split())
    tickers = tuple(extract_tickers(message, context.tickers))
    if not lowered or lowered in {"analyze", "analyse", "check this", "help", "compare"}:
        if not tickers and not context.source_urls:
            return IntentClassification(
                route="clarification_route",
                intent="missing_analysis_subject",
                confidence=0.96,
                clarification_question="Add a ticker, public source URL, or investment concept you want to explore.",
            )
    if context.source_urls and not tickers:
        return IntentClassification("source_analysis", "source_summary", 0.92)
    if len(tickers) > 1 or "compare" in lowered or "versus" in lowered or " vs " in f" {lowered} ":
        return IntentClassification("market_analysis", "security_comparison", 0.93, tickers=tickers)
    if tickers:
        return IntentClassification("market_analysis", "ticker_analysis", 0.94, tickers=tickers)
    if any(term in lowered for term in ("strategy", "risk tolerance", "horizon", "scenario")):
        return IntentClassification(
            "strategy_analysis",
            "educational_strategy_scenarios",
            0.88,
            requires_research_notes=True,
        )
    return IntentClassification(
        "research_explanation",
        "investment_concept_explanation",
        0.76,
        requires_research_notes=True,
    )
