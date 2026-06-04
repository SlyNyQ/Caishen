from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.llm.providers import ProviderRegistry
from app.orchestrator.workflow_engine import WorkflowEngine
from app.rag.retriever import KnowledgeRetriever, build_retriever
from app.tools.market_data import MarketDataClient, YFinanceMarketDataClient
from app.tools.web_sources import PublicSourceFetcher


@dataclass(slots=True)
class AppDependencies:
    settings: Settings
    provider_registry: ProviderRegistry
    market_data: MarketDataClient
    source_fetcher: PublicSourceFetcher
    retriever: KnowledgeRetriever | None
    workflow_engine: WorkflowEngine


def build_dependencies(
    settings: Settings | None = None,
    *,
    market_data: MarketDataClient | None = None,
    source_fetcher: PublicSourceFetcher | None = None,
    retriever: KnowledgeRetriever | None = None,
) -> AppDependencies:
    resolved_settings = settings or Settings.from_env()
    providers = ProviderRegistry(resolved_settings)
    resolved_market_data = market_data or YFinanceMarketDataClient()
    resolved_source_fetcher = source_fetcher or PublicSourceFetcher(
        timeout_seconds=resolved_settings.request_timeout_seconds,
        max_bytes=resolved_settings.source_max_bytes,
    )
    resolved_retriever = retriever if retriever is not None else build_retriever(resolved_settings)
    workflow_engine = WorkflowEngine(
        settings=resolved_settings,
        provider_registry=providers,
        market_data=resolved_market_data,
        source_fetcher=resolved_source_fetcher,
        retriever=resolved_retriever,
    )
    return AppDependencies(
        settings=resolved_settings,
        provider_registry=providers,
        market_data=resolved_market_data,
        source_fetcher=resolved_source_fetcher,
        retriever=resolved_retriever,
        workflow_engine=workflow_engine,
    )
