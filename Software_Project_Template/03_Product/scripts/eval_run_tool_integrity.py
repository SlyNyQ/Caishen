"""Verify that Caishen market tools expose unavailable data without invention."""

from __future__ import annotations

from chat_eval_common import build_payload, post_chat


def main() -> None:
    payload = post_chat(
        payload=build_payload(message="Analyze INVALIDTICKER", tickers=["INVALIDTICKER"])
    )
    snapshots = payload["analysis"]["market_snapshots"]
    assert snapshots and snapshots[0]["status"] in {"available", "unavailable", "stale"}
    assert payload["tool_traces"] and payload["tool_traces"][0]["name"] == "market_snapshot"
    if snapshots[0]["status"] != "available":
        assert snapshots[0].get("current_price") is None
    print("PASS: market tool integrity probe completed.")


if __name__ == "__main__":
    main()
