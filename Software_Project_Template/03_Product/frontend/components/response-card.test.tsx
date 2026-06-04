import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResponseCard } from "@/components/response-card";
import type { ChatResponse } from "@/lib/types";

const response: ChatResponse = {
  request_id: "req-1",
  session_id: "session-1",
  route: "strategy_scenario",
  provider: "mock",
  model: "deterministic-caishen",
  answer: "I can describe educational scenarios, not tell you what to buy.",
  analysis: {
    market_snapshots: [],
    key_takeaways: [],
    risk_notes: ["Concentration increases company-specific risk."],
    source_summaries: [],
    strategy_scenarios: ["A diversified long-horizon scenario can reduce concentration."]
  },
  tool_traces: [{ name: "scenario", arguments: {}, result: {}, warnings: [] }],
  citations: [],
  refusal: {
    category: "personalized_advice",
    message: "Caishen cannot issue personalized buy or sell instructions."
  },
  debug: { route_decision: "refuse" }
};

describe("ResponseCard", () => {
  it("renders safety boundaries, scenarios, provider metadata, and debug details", () => {
    render(<ResponseCard showDebug response={response} />);

    expect(screen.getByText(/not tell you what to buy/)).toBeInTheDocument();
    expect(screen.getByText("Safety boundary")).toBeInTheDocument();
    expect(screen.getByText(/cannot issue personalized buy or sell/)).toBeInTheDocument();
    expect(screen.getByText("Educational scenarios")).toBeInTheDocument();
    expect(screen.getByText("mock | deterministic-caishen")).toBeInTheDocument();
    expect(screen.getByText("Tool traces")).toBeInTheDocument();
    expect(screen.getByText("Debug metadata")).toBeInTheDocument();
  });

  it("hides debug details when debug display is not enabled", () => {
    render(<ResponseCard response={response} />);
    expect(screen.queryByText("Tool traces")).not.toBeInTheDocument();
    expect(screen.queryByText("Debug metadata")).not.toBeInTheDocument();
  });
});
