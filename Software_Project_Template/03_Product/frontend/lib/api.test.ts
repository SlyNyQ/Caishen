import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("frontend API client", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000";
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    vi.unstubAllEnvs();
  });

  it("returns backend health when the request succeeds", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok", app: "caishen", environment: "local" }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const { getHealth } = await import("@/lib/api");
    expect(await getHealth()).toEqual({ status: "ok", app: "caishen", environment: "local" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/health",
      expect.objectContaining({ method: "GET", cache: "no-store" })
    );
  });

  it("defaults to the CloudFront API prefix outside development", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const { getHealth } = await import("@/lib/api");
    await getHealth();
    expect(fetchMock).toHaveBeenCalledWith("/api/health", expect.any(Object));
  });

  it("posts provider and analysis context without account headers", async () => {
    const response = {
      request_id: "req-1",
      session_id: "session-1",
      route: "market_analysis",
      provider: "mock",
      model: "deterministic-caishen",
      answer: "AAPL data is available.",
      analysis: {
        market_snapshots: [],
        key_takeaways: [],
        risk_notes: [],
        source_summaries: [],
        strategy_scenarios: []
      },
      tool_traces: [],
      citations: [],
      refusal: null,
      debug: {}
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const { sendChat } = await import("@/lib/api");
    await sendChat({
      message: "Analyze AAPL",
      provider: "mock",
      analysis_context: {
        tickers: ["AAPL"],
        source_urls: [],
        risk_tolerance: "balanced",
        horizon: "long",
        goal: "Understand volatility"
      }
    });

    const request = fetchMock.mock.calls[0][1];
    expect(request.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(request.body)).toMatchObject({
      message: "Analyze AAPL",
      provider: "mock",
      analysis_context: { tickers: ["AAPL"] }
    });
  });

  it("raises useful errors for backend and HTML responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Backend failure", { status: 500 })));
    const { sendChat } = await import("@/lib/api");
    await expect(sendChat({ message: "Analyze AAPL" })).rejects.toThrow("Backend failure");

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<!DOCTYPE html><html></html>", {
          status: 200,
          headers: { "Content-Type": "text/html" }
        })
      )
    );
    await expect(sendChat({ message: "Analyze AAPL" })).rejects.toThrow(
      "The request likely reached the frontend HTML app or an HTML error page instead of FastAPI."
    );
  });
});
