"""Probe Caishen retrieval grounding and citation behavior."""

from __future__ import annotations

import argparse
import json
import sys

from chat_eval_common import build_payload, post_chat, summarize_payload, validate_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Caishen RAG probe.")
    parser.add_argument("--message", default="Explain volatility risk")
    parser.add_argument("--api-base-url")
    parser.add_argument("--require-citations", action="store_true")
    args = parser.parse_args()

    payload = post_chat(
        payload=build_payload(message=args.message, client_request_id="rag-eval"),
        api_base_url=args.api_base_url,
    )
    print(json.dumps(summarize_payload(payload), indent=2))
    failures = validate_payload(
        payload,
        expected_route="research_explanation",
        require_citations=args.require_citations,
    )
    if failures:
        print("\n".join(f"FAIL: {failure}" for failure in failures), file=sys.stderr)
        raise SystemExit(1)
    print("PASS: Caishen RAG probe completed.")


if __name__ == "__main__":
    main()
