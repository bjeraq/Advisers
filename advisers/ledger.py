"""Append majlis sessions to the recommendations ledger.

One CSV row per council session; later phases read this back to grade each
adviser's track record (who kept being right earns more weight).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional

LEDGER_PATH = "ledger/recommendations.csv"
FIELDS = [
    "timestamp", "ticker", "mode", "price", "scores_json",
    "judge_top_option", "report_path", "outcome_30d", "outcome_90d",
]


def append_row(
    ticker: str,
    mode: str,
    price: Optional[float],
    scores: dict[str, float],
    judge_top_option: str,
    report_path: str,
    ledger_path: str = LEDGER_PATH,
) -> None:
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    new = not os.path.exists(ledger_path)
    with open(ledger_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({
            "timestamp": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "ticker": ticker.upper(),
            "mode": mode,
            "price": f"{price:.2f}" if price is not None else "",
            "scores_json": json.dumps(scores, ensure_ascii=False),
            "judge_top_option": judge_top_option,
            "report_path": report_path,
            "outcome_30d": "",
            "outcome_90d": "",
        })


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="تسجيل جلسة مجلس في سجل التوصيات")
    p.add_argument("--ticker", required=True)
    p.add_argument("--mode", default="full")
    p.add_argument("--price", type=float, default=None)
    p.add_argument("--scores", default="{}", help='JSON مثل {"الفني": 4, "الدب": -6}')
    p.add_argument("--top-option", default="", help="الخيار الأول من حكم القاضي")
    p.add_argument("--report", default="")
    p.add_argument("--ledger", default=LEDGER_PATH)
    args = p.parse_args(argv)

    append_row(args.ticker, args.mode, args.price, json.loads(args.scores),
               args.top_option, args.report, args.ledger)
    print(f"سُجلت الجلسة في {args.ledger}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
