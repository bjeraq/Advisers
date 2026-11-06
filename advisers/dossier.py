"""Build the shared Arabic fact file (dossier) a majlis debate runs on.

Inputs are JSON files saved from the TradingView MCP tools (OHLCV bars,
financials snapshot, news headlines) plus the sharia universe CSV; the
output is one Markdown dossier every adviser argues from, so the whole
debate stands on the same numbers.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Optional

from . import indicators as ind
from .screener import load_universe

STATUS_AR = {
    "compliant": "متوافق ✅",
    "non_compliant": "غير متوافق ❌",
    "review": "يحتاج مراجعة ⚠️",
}

# TradingView financial keys worth showing, with Arabic labels.
FIN_LABELS = [
    ("price_earnings_ttm", "مكرر الربحية"),
    ("price_sales_ttm", "مكرر المبيعات"),
    ("price_book_fq", "مكرر القيمة الدفترية"),
    ("earnings_per_share_diluted_ttm", "ربح السهم"),
    ("revenue_ttm", "الإيرادات السنوية"),
    ("revenue_growth_ttm_yoy", "نمو الإيرادات سنوياً %"),
    ("net_income_ttm", "صافي الربح"),
    ("net_margin_ttm", "هامش صافي الربح %"),
    ("gross_margin_ttm", "الهامش الإجمالي %"),
    ("operating_margin_ttm", "الهامش التشغيلي %"),
    ("return_on_equity_fq", "العائد على حقوق المساهمين %"),
    ("return_on_assets_fq", "العائد على الأصول %"),
    ("free_cash_flow_ttm", "التدفق النقدي الحر"),
    ("ebitda_ttm", "الأرباح التشغيلية قبل الاستهلاك"),
    ("total_debt_fq", "إجمالي الديون"),
    ("cash_n_short_term_invest_fq", "النقد والاستثمارات القصيرة"),
    ("dividends_yield_current", "عائد التوزيعات %"),
]


def _load_json(path: Optional[str]):
    if not path:
        return None
    with open(path) as f:
        return json.load(f)


def _bars(payload) -> list[dict]:
    if payload is None:
        return []
    if isinstance(payload, dict):
        for key in ("bars", "rows", "data"):
            inner = payload.get(key)
            if isinstance(inner, (list, dict)):
                return _bars(inner)
        return []
    return [b for b in payload if isinstance(b, dict) and "c" in b]


def _news_items(payload) -> list[dict]:
    if payload is None:
        return []
    if isinstance(payload, dict):
        for key in ("headlines", "news", "items", "data"):
            inner = payload.get(key)
            if isinstance(inner, (list, dict)):
                return _news_items(inner)
        return []
    return [n for n in payload if isinstance(n, dict) and n.get("title")]


def _compact(n) -> str:
    if not isinstance(n, (int, float)):
        return str(n)
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.2f}{unit}"
    return f"{n:,.2f}"


def _ret(closes: list[float], days: int) -> Optional[float]:
    if len(closes) <= days or not closes[-1 - days]:
        return None
    return (closes[-1] / closes[-1 - days] - 1) * 100


def _fmt_pct(v: Optional[float]) -> str:
    return f"{v:+.1f}%" if v is not None else "—"


def technical_section(bars: list[dict]) -> list[str]:
    closes = [float(b["c"]) for b in bars]
    vols = [float(b.get("v") or 0) for b in bars]
    if len(closes) < 30:
        return ["بيانات الأسعار غير كافية للتحليل الفني."]
    last = closes[-1]
    out = [
        f"- آخر إغلاق: {last:,.2f}$",
        f"- العوائد: أسبوع {_fmt_pct(_ret(closes, 5))} / شهر {_fmt_pct(_ret(closes, 21))} / ٣ أشهر {_fmt_pct(_ret(closes, 63))}",
    ]
    hi90, lo90 = max(closes[-63:]), min(closes[-63:])
    out.append(
        f"- مدى ٣ أشهر: [{lo90:,.2f} — {hi90:,.2f}]، البعد عن القمة "
        f"{_fmt_pct((last / hi90 - 1) * 100)} وعن القاع {_fmt_pct((last / lo90 - 1) * 100)}"
    )
    if len(closes) >= 200:
        s50, s200 = ind.sma(closes, 50)[-1], ind.sma(closes, 200)[-1]
        cross = "تقاطع ذهبي (اتجاه صاعد)" if s50 > s200 else "تقاطع موت (اتجاه هابط)"
        pos = "فوق" if last > s50 else "تحت"
        out.append(f"- المتوسطات: 50 يوم {s50:,.2f} / 200 يوم {s200:,.2f} — {cross}، والسعر {pos} متوسط 50")
    rsi = ind.rsi(closes, 14)[-1]
    if rsi is not None:
        state = "تشبع بيعي" if rsi <= 30 else "تشبع شرائي" if rsi >= 70 else "حيادي"
        out.append(f"- مؤشر القوة النسبية (14): {rsi:.0f} — {state}")
    _, _, hist = ind.macd(closes)
    if hist[-1] is not None:
        prev = hist[-2] if hist[-2] is not None else hist[-1]
        trend = "يتحسن" if hist[-1] > prev else "يضعف"
        sign = "موجب" if hist[-1] > 0 else "سالب"
        out.append(f"- الماكد: المدرج {sign} و{trend}")
    lower, mid, upper = ind.bollinger(closes, 20)
    if mid[-1] is not None:
        width = upper[-1] - lower[-1]
        pos_pct = 0 if width == 0 else (last - lower[-1]) / width * 100
        out.append(f"- موضع السعر داخل قناة بولنجر: {pos_pct:.0f}% (0 = الحد الأدنى، 100 = الأعلى)")
    if len(vols) >= 20 and sum(vols[-21:-1]):
        ratio = vols[-1] / (sum(vols[-21:-1]) / 20)
        out.append(f"- حجم آخر جلسة مقابل متوسط 20 يوم: ×{ratio:.1f}")
    return out


def sharia_section(ticker: str, universe_path: Optional[str]) -> list[str]:
    if not universe_path:
        return ["لا توجد قائمة فحص."]
    try:
        row = load_universe(universe_path).get(ticker)
    except OSError:
        return ["قائمة الفحص غير متوفرة."]
    if not row:
        return ["السهم خارج نطاق قائمة الفحص الحالية (راجع يدوياً)."]
    lines = [f"- الحالة: {STATUS_AR.get(row['status'], row['status'])}"]
    if row.get("debt_ratio"):
        lines.append(f"- الديون / القيمة السوقية: {float(row['debt_ratio']):.0%} (الحد 30%)")
    if row.get("cash_ratio"):
        lines.append(f"- النقد / القيمة السوقية: {float(row['cash_ratio']):.0%} (الحد 30%)")
    lines.append(f"- السبب: {row.get('reasons', '')}")
    lines.append(f"- القطاع/الصناعة: {row.get('sector', '')} / {row.get('industry', '')}")
    return lines


def financial_section(payload) -> list[str]:
    if payload is None:
        return ["لم تُجلب بيانات مالية."]
    flat: dict = {}

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    flat.setdefault(k, v)
                elif isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(payload)
    lines = []
    for key, label in FIN_LABELS:
        if key in flat:
            lines.append(f"- {label}: {_compact(flat[key])}")
    return lines or ["البيانات المالية غير متاحة بالصيغة المتوقعة."]


def news_section(payload, limit: int = 12) -> list[str]:
    items = _news_items(payload)[:limit]
    if not items:
        return ["لا أخبار حديثة في المصدر."]
    lines = []
    for n in items:
        ts = n.get("published")
        day = (
            datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
            if isinstance(ts, (int, float)) else ""
        )
        provider = n.get("provider") or ""
        urgent = "🔴 " if n.get("urgency") == 1 else ""
        lines.append(f"- {urgent}{day} — {n['title']} ({provider})")
    return lines


def build(ticker: str, bars_path, fin_path, news_path, universe_path) -> str:
    bars = _bars(_load_json(bars_path))
    parts = [
        f"# ملف الحقائق — {ticker}",
        f"تاريخ الإعداد: {datetime.now(tz=timezone.utc).date().isoformat()}",
        "",
        "## الفحص الشرعي",
        *sharia_section(ticker, universe_path),
        "",
        "## الصورة الفنية (من بيانات الأسعار اليومية)",
        *technical_section(bars),
        "",
        "## المؤشرات المالية",
        *financial_section(_load_json(fin_path)),
        "",
        "## آخر الأخبار",
        *news_section(_load_json(news_path)),
        "",
        "> كل نقاش المجلس يستند حصراً للأرقام أعلاه. أي رقم غير مذكور هنا لا يُحتج به.",
    ]
    return "\n".join(parts)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="تجهيز ملف الحقائق لجلسة المجلس")
    p.add_argument("--ticker", required=True)
    p.add_argument("--bars", default=None, help="JSON من أداة الأسعار التاريخية")
    p.add_argument("--financials", default=None, help="JSON من أداة الماليات")
    p.add_argument("--news", default=None, help="JSON من أداة الأخبار")
    p.add_argument("--universe", default="data/universe_us.csv")
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)

    text = build(args.ticker.upper(), args.bars, args.financials, args.news,
                 args.universe)
    with open(args.out, "w") as f:
        f.write(text)
    print(f"جُهّز ملف الحقائق: {args.out} ({len(text)} حرف)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
