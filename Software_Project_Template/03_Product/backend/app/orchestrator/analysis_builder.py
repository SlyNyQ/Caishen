from __future__ import annotations

from typing import Any

from app.api.schemas import AnalysisContext
from app.tools.strategy_scenarios import build_strategy_scenarios


BASE_RISK_NOTES = [
    "Market data can be delayed, incomplete, or revised; verify time-sensitive values independently.",
    "This analysis is educational and is not personalized financial advice or a trade instruction.",
]


def build_analysis(
    *,
    context: AnalysisContext,
    market_snapshots: list[dict[str, Any]],
    source_summaries: list[dict[str, str]],
) -> dict[str, Any]:
    available = [snapshot for snapshot in market_snapshots if snapshot.get("status") == "available"]
    key_takeaways: list[str] = []
    risk_notes = list(BASE_RISK_NOTES)

    for snapshot in available:
        ticker = snapshot["ticker"]
        change = snapshot.get("percent_change")
        volatility = snapshot.get("annualized_volatility")
        if isinstance(change, (int, float)):
            key_takeaways.append(f"{ticker} changed {change:+.2f}% from its previous close.")
        if isinstance(volatility, (int, float)) and volatility >= 40:
            risk_notes.append(f"{ticker} shows elevated annualized volatility of about {volatility:.1f}%.")
    unavailable = [snapshot["ticker"] for snapshot in market_snapshots if snapshot.get("status") != "available"]
    if unavailable:
        risk_notes.append(f"Live market data was unavailable for: {', '.join(unavailable)}.")
    if source_summaries:
        key_takeaways.append(f"{len(source_summaries)} public source(s) were reviewed for additional context.")
    if not key_takeaways:
        key_takeaways.append("Use the cited research notes and defined investment context to frame further questions.")

    return {
        "market_snapshots": market_snapshots,
        "key_takeaways": key_takeaways[:6],
        "risk_notes": list(dict.fromkeys(risk_notes))[:8],
        "source_summaries": source_summaries,
        "strategy_scenarios": build_strategy_scenarios(context),
    }
