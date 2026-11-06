"""Normalising TradingView screener rows into plain dicts.

The Claude session fetches rows via the TradingView MCP tools and saves the
JSON result to a file; these helpers turn those rows into the stable shape
the rest of the package works with, so a change of data source only ever
touches this file.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from typing import Optional

ALLOWED_EXCHANGES = {"NASDAQ", "NYSE", "AMEX", "CBOE"}

SCAN_URL = "https://scanner.tradingview.com/america/scan"
SCAN_COLUMNS = [
    "name", "description", "exchange", "is_primary", "sector", "industry",
    "market_cap_basic", "total_debt_fq", "cash_n_short_term_invest_fq",
    "close", "change", "volume",
]


def _num(row: dict, key: str) -> Optional[float]:
    v = row.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def normalize(row: dict) -> dict:
    """Map one raw TradingView screener row to the package's quote shape."""
    symbol = row.get("symbol") or ""
    exchange = row.get("exchange") or (symbol.split(":")[0] if ":" in symbol else "")
    ticker = row.get("name") or (symbol.split(":")[-1] if symbol else "")
    return {
        "symbol": symbol or (f"{exchange}:{ticker}" if exchange and ticker else ticker),
        "ticker": ticker,
        "company": row.get("description") or ticker,
        "exchange": exchange,
        "is_primary": row.get("is_primary", True) is not False,
        "sector": row.get("sector") or "",
        "industry": row.get("industry") or "",
        "market_cap": _num(row, "market_cap_basic"),
        "total_debt": _num(row, "total_debt_fq"),
        "cash_sti": _num(row, "cash_n_short_term_invest_fq"),
        "close": _num(row, "close"),
        "change_pct": _num(row, "change"),
        "volume": _num(row, "volume"),
    }


def load_rows(path: str) -> list[dict]:
    """Load and normalize screener rows from a saved MCP JSON result.

    Accepts either the full tool result ({"data": {"rows": [...]}}), the
    data object, or a bare list of rows.
    """
    with open(path) as f:
        payload = json.load(f)
    if isinstance(payload, dict):
        payload = payload.get("data", payload)
    if isinstance(payload, dict):
        payload = payload.get("rows", [])
    return [
        r if "ticker" in r and "market_cap" in r else normalize(r)
        for r in payload
        if isinstance(r, dict)
    ]


def in_scope(q: dict, min_market_cap: float) -> bool:
    """Primary US-listed stock above the size floor."""
    return bool(
        q["is_primary"]
        and q["exchange"] in ALLOWED_EXCHANGES
        and q["ticker"]
        and (q["market_cap"] or 0) >= min_market_cap
    )


def _scan_page(body: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        SCAN_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "advisers/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fetch_scan(
    min_market_cap: float = 2e9,
    sort_by: str = "market_cap_basic",
    sort_order: str = "desc",
    max_rows: int = 5000,
    page_size: int = 1000,
    timeout: float = 30.0,
    retries: int = 2,
) -> list[dict]:
    """Fetch US stock rows straight from the TradingView scanner endpoint.

    Pages through results and returns normalized quotes. Used by the weekly
    sharia screen and the morning scout so bulk pulls stay out of the chat;
    the TradingView MCP connector remains the per-ticker/interactive source.
    """
    rows: list[dict] = []
    start = 0
    while start < max_rows:
        body = {
            "filter": [
                {"left": "market_cap_basic", "operation": "egreater",
                 "right": min_market_cap},
                {"left": "type", "operation": "equal", "right": "stock"},
                {"left": "is_primary", "operation": "equal", "right": True},
                {"left": "exchange", "operation": "in_range",
                 "right": sorted(ALLOWED_EXCHANGES)},
            ],
            "options": {"lang": "en"},
            "columns": SCAN_COLUMNS,
            "sort": {"sortBy": sort_by, "sortOrder": sort_order},
            "range": [start, min(start + page_size, max_rows)],
        }
        for attempt in range(retries + 1):
            try:
                payload = _scan_page(body, timeout)
                break
            except Exception:
                if attempt == retries:
                    raise
                time.sleep(2 ** attempt)
        batch = payload.get("data") or []
        for item in batch:
            raw = dict(zip(SCAN_COLUMNS, item.get("d", [])))
            raw["symbol"] = item.get("s", "")
            rows.append(normalize(raw))
        start += page_size
        if len(batch) < page_size or start >= payload.get("totalCount", 0):
            break
    return rows


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="سحب صفوف الأسعار من ماسح تريدنق فيو")
    p.add_argument("--out", required=True, help="ملف JSON للنتيجة")
    p.add_argument("--min-market-cap", type=float, default=2e9)
    p.add_argument("--sort-by", default="market_cap_basic")
    p.add_argument("--sort-order", default="desc", choices=["asc", "desc"])
    p.add_argument("--max-rows", type=int, default=5000)
    args = p.parse_args(argv)

    rows = fetch_scan(args.min_market_cap, args.sort_by, args.sort_order,
                      args.max_rows)
    with open(args.out, "w") as f:
        json.dump(rows, f)
    print(f"سُحب {len(rows)} سهم إلى {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
