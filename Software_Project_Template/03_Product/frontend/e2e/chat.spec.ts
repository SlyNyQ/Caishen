import { expect, test } from "@playwright/test";

const apiBaseUrl = "http://127.0.0.1:8000";

const analysis = {
  market_snapshots: [
    {
      ticker: "AAPL",
      company_name: "Apple Inc.",
      currency: "USD",
      current_price: 210.12,
      percent_change: 1.2,
      status: "available"
    }
  ],
  key_takeaways: ["AAPL has positive short-term momentum."],
  risk_notes: ["Historical returns do not guarantee future performance."],
  source_summaries: [],
  strategy_scenarios: []
};

test.beforeEach(async ({ page }) => {
  await page.route(`${apiBaseUrl}/health`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", app: "caishen", environment: "local" })
    });
  });
});

test("completes a structured market-analysis flow", async ({ page }) => {
  await page.route(`${apiBaseUrl}/chat`, async (route) => {
    const request = route.request().postDataJSON();
    expect(request.provider).toBe("openai");
    expect(request.analysis_context.tickers).toEqual(["AAPL"]);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        request_id: "req-e2e-1",
        session_id: "session-e2e-1",
        route: "market_analysis",
        provider: "openai",
        model: "gpt-4.1-mini",
        answer: "AAPL has positive short-term momentum, with meaningful market risk.",
        analysis,
        tool_traces: [],
        citations: [],
        refusal: null,
        debug: {}
      })
    });
  });

  await page.goto("/");
  await page.getByLabel("Analysis provider").selectOption("openai");
  await page.getByLabel("Tickers").fill("AAPL");
  await page.getByPlaceholder(/Ask Caishen to analyze a ticker/).fill("Analyze the evidence");
  await page.getByRole("button", { name: "Analyze" }).click();

  await expect(page.getByText(/positive short-term momentum, with meaningful market risk/)).toBeVisible();
  await expect(page.getByText("Apple Inc.")).toBeVisible();
  await expect(page.getByText("AAPL has positive short-term momentum.")).toBeVisible();
});

test("renders an educational safety boundary", async ({ page }) => {
  await page.route(`${apiBaseUrl}/chat`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        request_id: "req-e2e-2",
        session_id: "session-e2e-2",
        route: "refuse",
        provider: "mock",
        model: "deterministic-caishen",
        answer: "I can compare evidence and scenarios, but I cannot tell you what to buy.",
        analysis: { ...analysis, market_snapshots: [] },
        tool_traces: [],
        citations: [],
        refusal: {
          category: "personalized_advice",
          message: "Caishen cannot issue personalized buy or sell instructions."
        },
        debug: {}
      })
    });
  });

  await page.goto("/");
  await page.getByPlaceholder(/Ask Caishen to analyze a ticker/).fill("Tell me exactly what stock to buy");
  await page.getByRole("button", { name: "Analyze" }).click();

  await expect(page.getByText("Safety boundary")).toBeVisible();
  await expect(page.getByText(/cannot issue personalized buy or sell instructions/)).toBeVisible();
});

test("adapts the workspace for mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Think through an investment." })).toBeVisible();
  await expect(page.getByLabel("Analysis provider")).toBeVisible();
  await expect(page.getByText("Evidence at a glance")).toBeVisible();
});
