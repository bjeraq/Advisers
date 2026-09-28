"""Command-line entry point: python -m advisers AAPL MSFT --csv data.csv"""

from __future__ import annotations

import argparse
import sys

from .advisers import default_council
from .data import fetch_stooq, load_csv

DISCLAIMER = "Educational use only. This is not financial advice."


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="advisers", description=__doc__)
    p.add_argument("symbols", nargs="*", help="tickers to fetch from stooq.com")
    p.add_argument("--csv", action="append", default=[], help="local price CSV")
    args = p.parse_args(argv)
    if not args.symbols and not args.csv:
        p.error("give at least one symbol or --csv file")

    sources = [(s.upper(), lambda s=s: fetch_stooq(s)) for s in args.symbols]
    sources += [(path, lambda path=path: load_csv(path)) for path in args.csv]

    council = default_council()
    failed = 0
    for label, load in sources:
        try:
            bars = load()
        except Exception as e:  # network or parse errors: report and continue
            print(f"{label}: error: {e}", file=sys.stderr)
            failed += 1
            continue
        v = council.advise(bars)
        print(f"{label}  {bars[-1].day}  close {bars[-1].close:.2f}")
        print(f"  => {v.action}  (score {v.score:+.2f})")
        for s in v.signals:
            print(f"     {s.adviser:<10} {s.action:<4} {s.score:+.2f}  {s.reason}")
        print()
    print(DISCLAIMER)
    return 1 if failed == len(sources) else 0
