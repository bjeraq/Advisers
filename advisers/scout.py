"""Morning scout: build (and send) the daily halal movers message.

The scheduled session fetches two fresh screener snapshots (sorted by change
descending and ascending), saves them as JSON, then runs:

    python -m advisers.scout --rows gainers.json --rows losers.json --send

On US market holidays it exits quietly; on a data failure with --send it
sends a short apology message instead of staying silent.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from typing import Optional

from .movers import top_movers
from .quotes import load_rows
from .report import format_failure_message, format_morning_message
from .screener import load_universe
from .telegram import send_message

HOLIDAYS_FILE = "config/market_holidays_us.json"


def is_trading_day(day: date, holidays_file: str = HOLIDAYS_FILE) -> bool:
    if day.weekday() >= 5:
        return False
    try:
        with open(holidays_file) as f:
            holidays = set(json.load(f)["holidays"])
    except OSError:
        holidays = set()
    return day.isoformat() not in holidays


def build_message(
    row_files: list[str],
    universe_path: str,
    top: int,
    min_dollar_volume: float,
    asof: Optional[str] = None,
) -> str:
    rows: list[dict] = []
    for path in row_files:
        rows.extend(load_rows(path))
    if not rows:
        raise RuntimeError("ملفات الأسعار فاضية")
    gainers, losers = top_movers(
        rows, load_universe(universe_path), top, min_dollar_volume
    )
    if not gainers and not losers:
        raise RuntimeError("ما طلع ولا سهم متوافق في البيانات")
    return format_morning_message(gainers, losers, asof)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="راصد الصباح: رسالة الرابحين والخاسرين")
    p.add_argument("--rows", action="append", required=True)
    p.add_argument("--universe", default="data/universe_us.csv")
    p.add_argument("--top", type=int, default=5)
    p.add_argument("--min-dollar-volume", type=float, default=10e6)
    p.add_argument("--asof", default=None)
    p.add_argument("--send", action="store_true", help="أرسل فعلياً لتيليجرام")
    p.add_argument("--force", action="store_true", help="تجاهل فحص العطل (للتجارب)")
    args = p.parse_args(argv)

    today = date.fromisoformat(args.asof) if args.asof else date.today()
    if not args.force and not is_trading_day(today):
        print(f"{today} يوم عطلة بالسوق الأمريكي — ما فيه رسالة اليوم.")
        return 0

    try:
        message = build_message(
            args.rows, args.universe, args.top, args.min_dollar_volume, args.asof
        )
    except Exception as e:
        print(f"فشل تجهيز الرسالة: {e}", file=sys.stderr)
        if args.send:
            send_message(format_failure_message(str(e)))
            print("أُرسلت رسالة الاعتذار.")
        return 1

    if args.send:
        send_message(message)
        print("وصلت رسالة الصباح للقروب.")
    else:
        print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
