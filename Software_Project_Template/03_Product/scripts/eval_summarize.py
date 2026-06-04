"""Summarize Caishen JSONL evaluation results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    args = parser.parse_args()
    rows = [
        json.loads(line)
        for line in Path(args.input).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    passed = sum(bool(row.get("passed")) for row in rows)
    print(json.dumps({"scenarios": len(rows), "passed": passed, "failed": len(rows) - passed}, indent=2))


if __name__ == "__main__":
    main()
