"""Fetch recent TradingView headlines for the urgent-news guard.

The guard session fetches a recency window of headlines per symbol, reads
them itself to judge materiality, then sends alerts through the telegram
module using the urgent-message template.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from typing import Optional

from .report import format_urgent_message
from .telegram import send_message

URL = "https://news-headlines.tradingview.com/v2/headlines"
STORY_BASE = "https://www.tradingview.com"


def fetch(symbol: str, lang: str = "en", timeout: float = 20.0) -> list[dict]:
    qs = urllib.parse.urlencode({"symbol": symbol, "lang": lang, "client": "web"})
    req = urllib.request.Request(f"{URL}?{qs}", headers={
        "User-Agent": "advisers/1.0", "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.load(resp)
    return payload.get("items", []) if isinstance(payload, dict) else []


def normalize(item: dict) -> dict:
    link = item.get("link") or ""
    story = item.get("storyPath") or ""
    if not link and story:
        link = STORY_BASE + story
    return {
        "id": item.get("id", ""),
        "title": item.get("title", ""),
        "published": item.get("published"),
        "provider": item.get("source") or item.get("provider") or "",
        "urgency": item.get("urgency", 2),
        "link": link,
    }


def recent(items: list[dict], minutes: int, now: Optional[float] = None) -> list[dict]:
    now = now or time.time()
    floor = now - minutes * 60
    out = [
        normalize(i) for i in items
        if isinstance(i.get("published"), (int, float)) and i["published"] >= floor
    ]
    out.sort(key=lambda i: (-(i["urgency"] == 1), -(i["published"] or 0)))
    return out


def resolve_symbols(tickers: list[str], universe_path: str) -> list[str]:
    """Map bare tickers to EXCHANGE:TICKER via the universe file."""
    try:
        from .screener import load_universe
        uni = load_universe(universe_path)
    except OSError:
        uni = {}
    out = []
    for t in tickers:
        t = t.strip().upper()
        if not t:
            continue
        if ":" in t:
            out.append(t)
        elif t in uni and uni[t].get("symbol"):
            out.append(uni[t]["symbol"])
        else:
            out.append(f"NASDAQ:{t}")  # best-effort default
    return out


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="أخبار حديثة لرمز، أو إرسال تنبيه عاجل")
    p.add_argument("--symbol", help="رمز كامل مثل NASDAQ:NVDA أو مجرد NVDA")
    p.add_argument("--minutes", type=int, default=75)
    p.add_argument("--universe", default="data/universe_us.csv")
    p.add_argument("--out", default=None)
    p.add_argument("--alert", choices=["warning", "opportunity"],
                   help="أرسل تنبيهاً بدل الجلب")
    p.add_argument("--ticker", help="رمز السهم للتنبيه")
    p.add_argument("--headline", help="عنوان الخبر")
    p.add_argument("--why", help="لماذا يهمك هذا الخبر")
    p.add_argument("--link", default=None)
    p.add_argument("--send", action="store_true")
    args = p.parse_args(argv)

    if args.alert:
        if not (args.ticker and args.headline and args.why):
            p.error("التنبيه يحتاج --ticker و --headline و --why")
        msg = format_urgent_message(args.alert, args.ticker, args.headline,
                                    args.why, args.link)
        if args.send:
            send_message(msg)
            print("أُرسل التنبيه العاجل.")
        else:
            print(msg)
        return 0

    if not args.symbol:
        p.error("حدد --symbol أو --alert")
    symbol = resolve_symbols([args.symbol], args.universe)[0]
    items = recent(fetch(symbol), args.minutes)
    result = {"symbol": symbol, "window_minutes": args.minutes,
              "count": len(items), "items": items}
    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
        print(f"{symbol}: {len(items)} خبر خلال {args.minutes} دقيقة → {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
