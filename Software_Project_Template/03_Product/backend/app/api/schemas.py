from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ProviderName = Literal["mock", "openai", "anthropic", "google", "bedrock"]
RiskTolerance = Literal["unspecified", "conservative", "balanced", "growth"]
InvestmentHorizon = Literal["unspecified", "short", "medium", "long"]


class AnalysisContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tickers: list[str] = Field(default_factory=list, max_length=8)
    source_urls: list[str] = Field(default_factory=list, max_length=3)
    risk_tolerance: RiskTolerance = "unspecified"
    horizon: InvestmentHorizon = "unspecified"
    goal: str | None = Field(default=None, max_length=300)

    @field_validator("tickers")
    @classmethod
    def normalize_tickers(cls, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            ticker = value.strip().upper().lstrip("$")
            if ticker and ticker not in normalized:
                normalized.append(ticker)
        return normalized


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    title: str
    snippet: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    artifact_version: str | None = None


class Refusal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    message: str


class MarketSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    company_name: str
    currency: str | None = None
    current_price: float | None = None
    previous_close: float | None = None
    percent_change: float | None = None
    performance_1m: float | None = None
    performance_3m: float | None = None
    performance_1y: float | None = None
    annualized_volatility: float | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    data_as_of: str | None = None
    status: Literal["available", "unavailable", "stale"] = "available"
    note: str | None = None


class SourceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    title: str
    summary: str
    fetched_at: str
    status: Literal["available", "unavailable"] = "available"


class ResponseAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_snapshots: list[MarketSnapshot] = Field(default_factory=list)
    key_takeaways: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    source_summaries: list[SourceSummary] = Field(default_factory=list)
    strategy_scenarios: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    client_request_id: str | None = None
    provider: ProviderName | None = None
    model: str | None = Field(default=None, max_length=160)
    analysis_context: AnalysisContext = Field(default_factory=AnalysisContext)


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    session_id: str
    route: str
    provider: ProviderName
    model: str
    answer: str
    analysis: ResponseAnalysis = Field(default_factory=ResponseAnalysis)
    tool_traces: list[ToolTrace] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    refusal: Refusal | None = None
    debug: dict[str, Any] = Field(default_factory=dict)
