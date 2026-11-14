"""صائد المظلومات: strong companies whose stock got beaten down.

Finds compliant stocks that dropped hard recently while the business
itself still looks healthy (fat margins, high return on equity, light
debt). The scan only nominates candidates — the mazloum skill session then
reads each candidate's news to separate "punished by rumors/politics"
(interesting) from "punished for real deterioration" (excluded).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from .quotes import load_rows
from .screener import COMPLIANT, load_config, load_universe, universe_from_rows


def find_candidates(
    rows: list[dict],
    universe: dict[str, dict],
    max_perf_1m: float = -12.0,
    max_perf_1w: float = -8.0,
    min_margin: float = 5.0,
    max_debt_ratio: float = 0.25,
    min_dollar_volume: float = 20e6,
    top: int = 8,
) -> list[dict]:
    """Rank beaten-down quality stocks: deeper unjust drop + better business."""
    out = []
    for q in rows:
        u = universe.get(q.get("ticker", ""))
        if not u or u.get("status") != COMPLIANT:
            continue
        p1m, p1w = q.get("perf_1m"), q.get("perf_1w")
        dropped = (p1m is not None and p1m <= max_perf_1m) or (
            p1w is not None and p1w <= max_perf_1w
        )
        if not dropped:
            continue
        margin = q.get("net_margin")
        if margin is None or margin < min_margin:
            continue
        try:
            debt = float(u.get("debt_ratio") or 9)
        except (TypeError, ValueError):
            debt = 9.0
        if debt > max_debt_ratio:
            continue
        if (q.get("volume") or 0) * (q.get("close") or 0) < min_dollar_volume:
            continue
        roe = q.get("roe")
        drop = min(v for v in (p1m, p1w) if v is not None)
        # Cap ROE's contribution: near-zero equity makes ROE meaningless.
        quality = margin + min(roe or 0, 100) / 2
        why = (
            f"هبوط {drop:.0f}% خلال شهر مع هامش ربح صافٍ {margin:.0f}%"
            + (f" وعائد على الحقوق {roe:.0f}%" if roe is not None else "")
            + f" وديون {debt:.0%} فقط من القيمة السوقية"
        )
        out.append({
            **q,
            "debt_ratio": debt,
            "drop_pct": drop,
            "quality": quality,
            "score": -drop * (1 + quality / 100),
            "why_ar": why,
        })
    out.sort(key=lambda c: -c["score"])
    return out[:top]


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="ترشيح الأسهم المظلومة: هبوط حاد مع أساسيات قوية"
    )
    p.add_argument("--rows", action="append", required=True)
    p.add_argument("--universe", default="data/universe_us.csv")
    p.add_argument("--fresh-universe", action="store_true",
                   help="احسب القائمة الشرعية من صفوف اليوم نفسها بدل ملف المستودع")
    p.add_argument("--screening-config", default="config/screening.json")
    p.add_argument("--top", type=int, default=8)
    p.add_argument("--max-perf-1m", type=float, default=-12.0)
    p.add_argument("--max-perf-1w", type=float, default=-8.0)
    p.add_argument("--min-margin", type=float, default=5.0)
    p.add_argument("--max-debt-ratio", type=float, default=0.25)
    p.add_argument("--min-dollar-volume", type=float, default=20e6)
    args = p.parse_args(argv)

    rows: list[dict] = []
    for path in args.rows:
        rows.extend(load_rows(path))
    if args.fresh_universe:
        universe = universe_from_rows(rows, load_config(args.screening_config))
    else:
        universe = load_universe(args.universe)
    cands = find_candidates(
        rows, universe,
        args.max_perf_1m, args.max_perf_1w, args.min_margin,
        args.max_debt_ratio, args.min_dollar_volume, args.top,
    )
    slim = [
        {k: c.get(k) for k in (
            "ticker", "symbol", "company", "sector", "industry", "close",
            "perf_1w", "perf_1m", "net_margin", "roe", "debt_ratio",
            "drop_pct", "score", "why_ar",
        )}
        for c in cands
    ]
    print(json.dumps({"count": len(slim), "candidates": slim},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
