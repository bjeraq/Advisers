"""Sharia (halal) screening over TradingView fundamentals rows.

Methodology, in the spirit of the widely used AAOIFI-style equity screens
(all thresholds and lists live in config/screening.json):

- business filter: industries on the excluded list are non-compliant, and
  mixed businesses on the review list need a human look;
- ratio filter: total debt / market cap and (cash + short-term
  investments) / market cap must each stay under their thresholds.

The status is three-way: compliant / non_compliant / review. This is a
technical approximation, not a fatwa — revenue-purity data is not available
from free sources, so mixed businesses land in "review" instead of being
given a confidence we do not have.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from typing import Optional

from .quotes import in_scope, load_rows

COMPLIANT, NON_COMPLIANT, REVIEW = "compliant", "non_compliant", "review"

UNIVERSE_FIELDS = [
    "ticker", "symbol", "company", "exchange", "sector", "industry",
    "market_cap", "debt_ratio", "cash_ratio", "status", "reasons", "asof",
]


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _keyword_hit(text: str, words: list[str]) -> Optional[str]:
    for w in words:
        if re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE):
            return w
    return None


def classify(q: dict, cfg: dict) -> dict:
    """Return the quote extended with status, ratios and Arabic reasons."""
    reasons: list[str] = []
    status = COMPLIANT
    mcap = q["market_cap"]

    def ratio(v: Optional[float]) -> Optional[float]:
        return None if (v is None or not mcap) else v / mcap

    debt_r, cash_r = ratio(q["total_debt"]), ratio(q["cash_sti"])

    bad_kw = _keyword_hit(q["company"], cfg.get("excluded_keywords", []))
    if q["industry"] in cfg["excluded_industries"] or bad_kw:
        status = NON_COMPLIANT
        reasons.append(f"نشاط غير متوافق: {q['industry'] or bad_kw}")
    else:
        if debt_r is None or cash_r is None:
            status = REVIEW
            reasons.append("بيانات مالية ناقصة")
        else:
            if debt_r > cfg["max_debt_to_market_cap"]:
                status = NON_COMPLIANT
                reasons.append(f"الديون {debt_r:.0%} من القيمة السوقية")
            if cash_r > cfg["max_cash_to_market_cap"]:
                status = NON_COMPLIANT
                reasons.append(f"النقد والاستثمارات {cash_r:.0%} من القيمة السوقية")
        review_kw = _keyword_hit(q["company"], cfg.get("review_keywords", []))
        if status != NON_COMPLIANT and (
            q["industry"] in cfg["review_industries"] or review_kw
        ):
            status = REVIEW
            reasons.append(f"نشاط مختلط يحتاج مراجعة: {q['industry'] or review_kw}")

    if status == COMPLIANT:
        reasons.append("اجتاز فلتر النشاط والنسب")

    overrides = cfg.get("overrides", {})
    for forced, tickers in overrides.items():
        if q["ticker"] in tickers:
            status = forced
            reasons = [f"قرار يدوي من الإعدادات: {forced}"]
            break
    return {
        **q,
        "status": status,
        "debt_ratio": debt_r,
        "cash_ratio": cash_r,
        "reasons": "؛ ".join(reasons),
    }


def screen_rows(rows: list[dict], cfg: dict) -> list[dict]:
    results = [
        classify(q, cfg)
        for q in rows
        if in_scope(q, cfg["min_market_cap_usd"])
    ]
    results.sort(key=lambda r: -(r["market_cap"] or 0))
    return results


def write_universe(results: list[dict], path: str, asof: Optional[str] = None) -> None:
    asof = asof or date.today().isoformat()
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=UNIVERSE_FIELDS)
        w.writeheader()
        for r in results:
            w.writerow({
                **{k: r.get(k, "") for k in UNIVERSE_FIELDS},
                "market_cap": f"{r['market_cap']:.0f}" if r["market_cap"] else "",
                "debt_ratio": f"{r['debt_ratio']:.4f}" if r["debt_ratio"] is not None else "",
                "cash_ratio": f"{r['cash_ratio']:.4f}" if r["cash_ratio"] is not None else "",
                "asof": asof,
            })


def load_universe(path: str) -> dict[str, dict]:
    with open(path, newline="") as f:
        return {r["ticker"]: r for r in csv.DictReader(f)}


def universe_from_rows(rows: list[dict], cfg: dict) -> dict[str, dict]:
    """Screen fresh scan rows in memory: {ticker: result}, no file needed.

    Lets scheduled sessions work from today's data without writing to the
    repository; the committed CSV stays as a human-reviewable snapshot.
    """
    return {r["ticker"]: r for r in screen_rows(rows, cfg)}


def summarize(results: list[dict]) -> str:
    counts = {COMPLIANT: 0, NON_COMPLIANT: 0, REVIEW: 0}
    for r in results:
        counts[r["status"]] += 1
    return (
        f"المجموع {len(results)} سهم: "
        f"متوافق {counts[COMPLIANT]} / "
        f"غير متوافق {counts[NON_COMPLIANT]} / "
        f"يحتاج مراجعة {counts[REVIEW]}"
    )


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="الفحص الشرعي: صفوف الماسح -> قائمة الأسهم")
    p.add_argument("--rows", required=True, help="ملف JSON بصفوف الماسح المحفوظة")
    p.add_argument("--config", default="config/screening.json")
    p.add_argument("--out", default="data/universe_us.csv")
    p.add_argument("--asof", default=None)
    args = p.parse_args(argv)

    cfg = load_config(args.config)
    results = screen_rows(load_rows(args.rows), cfg)
    write_universe(results, args.out, args.asof)
    print(summarize(results))
    print(f"حُفظت القائمة في {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
