from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
import pandas as pd
import pytest

from app.api.schemas import AnalysisContext
from app.config import Settings
from app.dependencies import build_dependencies
from app.errors import ResourceNotReadyError, ValidationError
from app.llm.providers import ProviderRegistry
from app.main import create_app
from app.orchestrator.intent_classifier import classify_intent
from app.orchestrator.refusal_classifier import classify_refusal_intent
from app.rag.retriever import KnowledgeRetriever
from app.tools.market_data import MarketDataUnavailable, build_market_snapshot, extract_tickers
from app.tools.web_sources import UnsafeSourceUrl, validate_public_url


def settings(tmp_path: Path) -> Settings:
    return Settings(
        app_name="caishen",
        app_env="test",
        debug=False,
        log_level="INFO",
        cors_origins=("http://localhost:3000",),
        max_message_chars=4000,
        default_provider="mock",
        openai_model="gpt-4.1-mini",
        anthropic_model="claude-sonnet-4-5",
        google_model="gemini-2.0-flash",
        bedrock_model="amazon.nova-micro-v1:0",
        aws_region="eu-west-2",
        request_timeout_seconds=2,
        source_max_bytes=10_000,
        use_local_rag=False,
        kb_chunks_path=tmp_path / "chunks.jsonl",
        enable_debug_traces=True,
    )


class FakeMarketData:
    def get_snapshot(self, ticker: str) -> dict[str, object]:
        if ticker == "BAD":
            raise MarketDataUnavailable("No verified market data is available for BAD.")
        return {
            "ticker": ticker,
            "company_name": f"{ticker} Holdings",
            "currency": "USD",
            "current_price": 104.0,
            "previous_close": 100.0,
            "percent_change": 4.0,
            "performance_1m": 8.0,
            "performance_3m": 12.0,
            "performance_1y": 24.0,
            "annualized_volatility": 31.0,
            "data_as_of": datetime.now(timezone.utc).isoformat(),
            "status": "available",
            "note": "Fixture data.",
        }


class FakeSourceFetcher:
    def fetch(self, url: str) -> dict[str, str]:
        return {
            "url": url,
            "title": "Public earnings release",
            "summary": "Revenue increased while management highlighted demand uncertainty.",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "status": "available",
        }


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app_settings = settings(tmp_path)
    retriever = KnowledgeRetriever(
        [
            {
                "doc_id": "volatility",
                "chunk_id": 0,
                "title": "Volatility Risk",
                "text": "Volatility measures the size and frequency of price movements and does not predict direction.",
                "metadata": {"type": "risk"},
            }
        ]
    )
    dependencies = build_dependencies(
        app_settings,
        market_data=FakeMarketData(),
        source_fetcher=FakeSourceFetcher(),
        retriever=retriever,
    )
    return TestClient(create_app(app_settings, dependencies=dependencies))


def test_extract_tickers_combines_context_and_message() -> None:
    assert extract_tickers("Compare $AAPL and MSFT", ["NVDA"]) == ["NVDA", "AAPL", "MSFT"]


def test_market_snapshot_calculates_returns_and_volatility() -> None:
    history = pd.DataFrame(
        {"Close": [100.0, 102.0, 101.0, 104.0]},
        index=pd.date_range("2026-01-01", periods=4),
    )
    snapshot = build_market_snapshot("TEST", history=history, info={"longName": "Test Corp", "currency": "USD"})
    assert snapshot["current_price"] == 104.0
    assert snapshot["percent_change"] == pytest.approx(2.97, abs=0.01)
    assert snapshot["annualized_volatility"] > 0


def test_public_url_validation_blocks_private_networks() -> None:
    with pytest.raises(UnsafeSourceUrl):
        validate_public_url("http://localhost:8000/secret")
    with pytest.raises(UnsafeSourceUrl):
        validate_public_url("https://example.com", resolver=lambda _: ["127.0.0.1"])
    assert validate_public_url("https://example.com/report", resolver=lambda _: ["93.184.216.34"]).startswith("https://")


def test_intent_routing_and_refusal() -> None:
    comparison = classify_intent("Compare AAPL versus MSFT", AnalysisContext())
    assert comparison.route == "market_analysis"
    assert comparison.intent == "security_comparison"
    refusal = classify_refusal_intent("Buy AAPL for me now")
    assert not refusal.allowed
    assert refusal.intent == "trade_execution"


def test_provider_selection_enforces_allowlist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    registry = ProviderRegistry(settings(tmp_path))
    assert registry.resolve("mock", None) == ("mock", "caishen-mock")
    with pytest.raises(ValidationError):
        registry.resolve("mock", "unapproved-model")
    with pytest.raises(ResourceNotReadyError):
        registry.resolve("openai", None)


def test_health_and_ready_contracts(client: TestClient) -> None:
    assert client.get("/health").json()["app"] == "caishen"
    ready = client.get("/ready").json()
    assert ready["status"] == "ready"
    assert ready["default_provider"] == "mock"


def test_market_analysis_returns_structured_insights(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={
            "message": "Compare AAPL and MSFT for a long-term goal",
            "provider": "mock",
            "analysis_context": {
                "tickers": ["AAPL", "MSFT"],
                "risk_tolerance": "balanced",
                "horizon": "long",
                "goal": "evaluate durable growth",
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "market_analysis"
    assert payload["provider"] == "mock"
    assert len(payload["analysis"]["market_snapshots"]) == 2
    assert payload["analysis"]["strategy_scenarios"]
    assert len(payload["tool_traces"]) == 2


def test_source_analysis_returns_public_source_citation(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={
            "message": "Summarize this source",
            "provider": "mock",
            "analysis_context": {"source_urls": ["https://example.com/earnings"]},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "source_analysis"
    assert payload["analysis"]["source_summaries"][0]["status"] == "available"
    assert payload["citations"][0]["title"] == "Public earnings release"


def test_unavailable_market_data_is_not_invented(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={
            "message": "Analyze BAD",
            "provider": "mock",
            "analysis_context": {"tickers": ["BAD"]},
        },
    )
    snapshot = response.json()["analysis"]["market_snapshots"][0]
    assert snapshot["status"] == "unavailable"
    assert snapshot["current_price"] is None


def test_trade_execution_is_refused(client: TestClient) -> None:
    response = client.post("/chat", json={"message": "Buy AAPL for me now", "provider": "mock"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "refusal_route"
    assert payload["refusal"]["category"] == "trade_execution"


def test_rag_research_explanation_is_grounded(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={"message": "Explain volatility risk", "provider": "mock"},
    )
    payload = response.json()
    assert payload["route"] == "research_explanation"
    assert payload["citations"]
    assert payload["citations"][0]["title"] == "Volatility Risk"
