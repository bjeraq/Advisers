"""Loading daily price bars from CSV files or the free Stooq endpoint."""

from __future__ import annotations

import csv
import io
import urllib.request
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Bar:
    day: date
    open: float
    high: float
    low: float
    close: float
    volume: float


def _parse_rows(rows) -> list[Bar]:
    bars = []
    for row in rows:
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        close = row.get("adj close") or row.get("close")
        if not row.get("date") or not close or close.lower() == "null":
            continue
        bars.append(
            Bar(
                day=date.fromisoformat(row["date"]),
                open=float(row.get("open") or close),
                high=float(row.get("high") or close),
                low=float(row.get("low") or close),
                close=float(close),
                volume=float(row.get("volume") or 0),
            )
        )
    bars.sort(key=lambda b: b.day)
    return bars


def load_csv(path: str) -> list[Bar]:
    """Load bars from a CSV with Date/Open/High/Low/Close/Volume columns.

    Yahoo Finance and Stooq exports both work. "Adj Close" is preferred
    over "Close" when present.
    """
    with open(path, newline="") as f:
        return _parse_rows(csv.DictReader(f))


def fetch_stooq(symbol: str, timeout: float = 15.0) -> list[Bar]:
    """Download daily history from stooq.com (US tickers get a .us suffix)."""
    sym = symbol.lower()
    if "." not in sym:
        sym += ".us"
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    bars = _parse_rows(csv.DictReader(io.StringIO(text)))
    if not bars:
        raise ValueError(f"No data returned for {symbol!r}")
    return bars
