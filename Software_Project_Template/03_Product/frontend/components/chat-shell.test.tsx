import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatShell } from "@/components/chat-shell";

const { getHealthMock, sendChatMock } = vi.hoisted(() => ({
  getHealthMock: vi.fn(),
  sendChatMock: vi.fn()
}));

vi.mock("@/lib/api", () => ({
  getHealth: getHealthMock,
  sendChat: sendChatMock
}));

const emptyAnalysis = {
  market_snapshots: [],
  key_takeaways: [],
  risk_notes: [],
  source_summaries: [],
  strategy_scenarios: []
};

describe("ChatShell", () => {
  beforeEach(() => {
    getHealthMock.mockReset();
    sendChatMock.mockReset();
  });

  it("shows backend unavailable when the health check fails", async () => {
    getHealthMock.mockRejectedValue(new Error("Failed to fetch"));
    render(<ChatShell />);

    expect(await screen.findByText("Backend unavailable")).toBeInTheDocument();
    expect(screen.getByText("Failed to fetch")).toBeInTheDocument();
  });

  it("submits provider and research context, then renders structured insights", async () => {
    const user = userEvent.setup();
    getHealthMock.mockResolvedValue({ status: "ok", environment: "local" });
    sendChatMock.mockResolvedValue({
      request_id: "req-123",
      session_id: "session-123",
      route: "market_analysis",
      provider: "openai",
      model: "gpt-4.1-mini",
      answer: "AAPL has positive one-month momentum, with meaningful volatility risk.",
      analysis: {
        ...emptyAnalysis,
        key_takeaways: ["Momentum is positive."],
        market_snapshots: [
          {
            ticker: "AAPL",
            company_name: "Apple Inc.",
            currency: "USD",
            current_price: 210,
            percent_change: 1.2,
            status: "available"
          }
        ]
      },
      tool_traces: [],
      citations: [],
      refusal: null,
      debug: {}
    });

    render(<ChatShell />);
    await user.selectOptions(screen.getByLabelText("Analysis provider"), "openai");
    await user.type(screen.getByLabelText("Tickers"), "AAPL");
    await user.selectOptions(screen.getByLabelText("Risk tolerance"), "balanced");
    await user.type(
      screen.getByPlaceholderText(/Ask Caishen to analyze a ticker/),
      "Assess the evidence"
    );
    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(await screen.findByText(/positive one-month momentum/)).toBeInTheDocument();
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument();
    expect(screen.getByText("Momentum is positive.")).toBeInTheDocument();
    expect(sendChatMock).toHaveBeenCalledWith({
      message: "Assess the evidence",
      session_id: null,
      provider: "openai",
      analysis_context: {
        tickers: ["AAPL"],
        source_urls: [],
        risk_tolerance: "balanced",
        horizon: "unspecified",
        goal: null
      }
    });
  });

  it("renders a useful analysis error message", async () => {
    const user = userEvent.setup();
    getHealthMock.mockResolvedValue({ status: "ok", environment: "local" });
    sendChatMock.mockRejectedValue(new Error("Backend timed out"));

    render(<ChatShell />);
    await user.type(screen.getByPlaceholderText(/Ask Caishen to analyze a ticker/), "Compare AAPL");
    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(await screen.findByText("Analysis request failed: Backend timed out")).toBeInTheDocument();
  });

  it("fills the composer from a quick prompt and restores focus after a response", async () => {
    const user = userEvent.setup();
    getHealthMock.mockResolvedValue({ status: "ok", environment: "local" });
    sendChatMock.mockResolvedValue({
      request_id: "req-quick",
      session_id: "session-quick",
      route: "education",
      provider: "mock",
      model: "deterministic-caishen",
      answer: "Volatility describes the range and speed of price changes.",
      analysis: emptyAnalysis,
      tool_traces: [],
      citations: [],
      refusal: null,
      debug: {}
    });

    render(<ChatShell />);
    await user.click(screen.getByRole("button", { name: "Explain volatility risk" }));
    const input = screen.getByPlaceholderText(/Ask Caishen to analyze a ticker/);
    expect(input).toHaveValue("Explain volatility risk");
    await user.click(screen.getByRole("button", { name: "Analyze" }));
    await waitFor(() => expect(input).toHaveFocus());
  });
});
