"""Pick the top halal gainers and losers from fresh quote rows."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from .quotes import load_rows
from .screener import COMPLIANT, load_universe


def compliant_tickers(universe: dict[str, dict]) -> set[str]:
    return {t for t, r in universe.items() if r.get("status") == COMPLIANT}


def _dollar_volume(q: dict) -> float:
    return (q["volume"] or 0) * (q["close"] or 0)


def top_movers(
    rows: list[dict],
    universe: dict[str, dict],
    top: int = 5,
    min_dollar_volume: float = 10e6,
) -> tuple[list[dict], list[dict]]:
    """Return (gainers, losers) among compliant tickers, by % change.

    Rows are deduplicated per company (multiple share classes keep the most
    liquid line) and filtered by a minimum traded dollar volume so an
    illiquid blip never tops the list.
    """
    ok = compliant_tickers(universe)
    best: dict[str, dict] = {}
    for q in rows:
        if q["ticker"] not in ok or q["change_pct"] is None:
            continue
        if _dollar_volume(q) < min_dollar_volume:
            continue
        key = q["company"].split(" - ")[0].strip().lower()
        cur = best.get(key)
        if cur is None or _dollar_volume(q) > _dollar_volume(cur):
            best[key] = q
    ranked = sorted(best.values(), key=lambda q: q["change_pct"], reverse=True)
    gainers = [q for q in ranked if q["change_pct"] > 0][:top]
    losers = [q for q in reversed(ranked) if q["change_pct"] < 0][:top]
    return gainers, losers


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="أعلى الرابحين والخاسرين من الأسهم المتوافقة")
    p.add_argument("--rows", action="append", required=True,
                   help="ملف JSON بصفوف أسعار حديثة (يتكرر لأكثر من ملف)")
    p.add_argument("--universe", default="data/universe_us.csv")
    p.add_argument("--top", type=int, default=5)
    p.add_argument("--min-dollar-volume", type=float, default=10e6)
    args = p.parse_args(argv)

    rows: list[dict] = []
    for path in args.rows:
        rows.extend(load_rows(path))
    gainers, losers = top_movers(
        rows, load_universe(args.universe), args.top, args.min_dollar_volume
    )
    print(json.dumps({"gainers": gainers, "losers": losers},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
