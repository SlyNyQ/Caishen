"use client";

import type { AnalysisContext, InvestmentHorizon, RiskTolerance } from "@/lib/types";

type ContextBarProps = {
  context: AnalysisContext;
  onChange: (context: AnalysisContext) => void;
};

function parseList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ContextBar({ context, onChange }: ContextBarProps) {
  return (
    <section className="context-bar" aria-label="Analysis context">
      <label>
        <span>Tickers</span>
        <input
          aria-label="Tickers"
          value={context.tickers.join(", ")}
          onChange={(event) =>
            onChange({ ...context, tickers: parseList(event.target.value).map((ticker) => ticker.toUpperCase()) })
          }
          placeholder="AAPL, MSFT"
        />
      </label>
      <label>
        <span>Public source</span>
        <input
          aria-label="Public source URL"
          value={context.source_urls.join(", ")}
          onChange={(event) => onChange({ ...context, source_urls: parseList(event.target.value) })}
          placeholder="https://..."
        />
      </label>
      <label>
        <span>Risk</span>
        <select
          aria-label="Risk tolerance"
          value={context.risk_tolerance}
          onChange={(event) =>
            onChange({ ...context, risk_tolerance: event.target.value as RiskTolerance })
          }
        >
          <option value="unspecified">Not set</option>
          <option value="conservative">Conservative</option>
          <option value="balanced">Balanced</option>
          <option value="growth">Growth</option>
        </select>
      </label>
      <label>
        <span>Horizon</span>
        <select
          aria-label="Investment horizon"
          value={context.horizon}
          onChange={(event) => onChange({ ...context, horizon: event.target.value as InvestmentHorizon })}
        >
          <option value="unspecified">Not set</option>
          <option value="short">Short</option>
          <option value="medium">Medium</option>
          <option value="long">Long</option>
        </select>
      </label>
      <label className="goal-field">
        <span>Goal</span>
        <input
          aria-label="Investment goal"
          value={context.goal || ""}
          onChange={(event) => onChange({ ...context, goal: event.target.value || null })}
          placeholder="Understand long-term growth"
        />
      </label>
    </section>
  );
}
