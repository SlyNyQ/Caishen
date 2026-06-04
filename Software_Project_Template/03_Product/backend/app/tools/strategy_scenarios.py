from __future__ import annotations

from app.api.schemas import AnalysisContext


def build_strategy_scenarios(context: AnalysisContext) -> list[str]:
    horizon = context.horizon
    risk = context.risk_tolerance
    goal = context.goal or "understand the investment opportunity"

    scenarios = [
        f"Research scenario: verify the business, valuation, and major risks before acting on the goal to {goal}.",
        "Diversification scenario: compare the idea with a broad-market alternative instead of relying on one security.",
    ]
    if horizon == "short":
        scenarios.append("Short-horizon scenario: prioritize liquidity, event risk, and the possibility of rapid losses.")
    elif horizon == "long":
        scenarios.append("Long-horizon scenario: track fundamentals, valuation changes, and thesis-breaking developments over time.")
    else:
        scenarios.append("Time-horizon scenario: define when the capital may be needed before evaluating an investment approach.")

    if risk == "conservative":
        scenarios.append("Conservative scenario: use smaller exposure and emphasize capital preservation and downside limits.")
    elif risk == "growth":
        scenarios.append("Growth scenario: accept wider price swings only if the downside remains affordable.")
    else:
        scenarios.append("Balanced scenario: weigh upside potential against volatility, concentration, and drawdown risk.")
    return scenarios
