export type ProviderName = "mock" | "openai" | "anthropic" | "google" | "bedrock";
export type RiskTolerance = "unspecified" | "conservative" | "balanced" | "growth";
export type InvestmentHorizon = "unspecified" | "short" | "medium" | "long";

export interface AnalysisContext {
  tickers: string[];
  source_urls: string[];
  risk_tolerance: RiskTolerance;
  horizon: InvestmentHorizon;
  goal: string | null;
}

export interface Citation {
  doc_id: string;
  title: string;
  snippet: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface ToolTrace {
  name: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
  warnings: string[];
  artifact_version?: string | null;
}

export interface Refusal {
  category: string;
  message: string;
}

export interface MarketSnapshot {
  ticker: string;
  company_name: string;
  currency?: string | null;
  current_price?: number | null;
  previous_close?: number | null;
  percent_change?: number | null;
  performance_1m?: number | null;
  performance_3m?: number | null;
  performance_1y?: number | null;
  annualized_volatility?: number | null;
  market_cap?: number | null;
  pe_ratio?: number | null;
  data_as_of?: string | null;
  status: "available" | "unavailable" | "stale";
  note?: string | null;
}

export interface SourceSummary {
  url: string;
  title: string;
  summary: string;
  fetched_at: string;
  status: "available" | "unavailable";
}

export interface ResponseAnalysis {
  market_snapshots: MarketSnapshot[];
  key_takeaways: string[];
  risk_notes: string[];
  source_summaries: SourceSummary[];
  strategy_scenarios: string[];
}

export interface ChatRequest {
  message: string;
  session_id?: string | null;
  client_request_id?: string | null;
  provider?: ProviderName;
  model?: string | null;
  analysis_context?: AnalysisContext;
}

export interface ChatResponse {
  request_id: string;
  session_id: string;
  route: string;
  provider: ProviderName;
  model: string;
  answer: string;
  analysis: ResponseAnalysis;
  tool_traces: ToolTrace[];
  citations: Citation[];
  refusal: Refusal | null;
  debug: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  app?: string;
  environment?: string;
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}
