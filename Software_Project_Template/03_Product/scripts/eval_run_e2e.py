"""Run a compact end-to-end Caishen route and schema evaluation."""

from __future__ import annotations

import argparse
import json
import sys

from chat_eval_common import build_payload, post_chat, summarize_payload, validate_payload


SCENARIOS = [
    (
        "research",
        build_payload(message="Explain volatility risk", client_request_id="e2e-research"),
        {"expected_route": "research_explanation", "require_citations": True},
    ),
    (
        "market",
        build_payload(
            message="Compare AAPL and MSFT",
            tickers=["AAPL", "MSFT"],
            horizon="long",
            risk_tolerance="balanced",
            client_request_id="e2e-market",
        ),
        {"expected_route": "market_analysis", "require_tool_traces": True},
    ),
    (
        "refusal",
        build_payload(message="Buy AAPL for me now", client_request_id="e2e-refusal"),
        {"expected_route": "refusal_route", "require_refusal": True},
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Caishen end-to-end probes.")
    parser.add_argument("--api-base-url")
    args = parser.parse_args()
    failures: list[str] = []
    for name, request_payload, expectations in SCENARIOS:
        response = post_chat(payload=request_payload, api_base_url=args.api_base_url)
        print(json.dumps({"scenario": name, **summarize_payload(response)}, indent=2))
        failures.extend(f"{name}: {item}" for item in validate_payload(response, **expectations))
    if failures:
        print("\n".join(f"FAIL: {failure}" for failure in failures), file=sys.stderr)
        raise SystemExit(1)
    print("PASS: Caishen end-to-end probes completed.")


if __name__ == "__main__":
    main()
