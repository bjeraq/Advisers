"""Arabic message formatting for Telegram (HTML parse mode)."""

from __future__ import annotations

import html
from datetime import date
from typing import Optional

RLM = "‏"  # right-to-left mark keeps mixed Arabic/Latin lines readable
DISCLAIMER = "⚠️ للمعلومة فقط وليست توصية بيع أو شراء — القرار قرارك."


def _compact(n: Optional[float]) -> str:
    if n is None:
        return "—"
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.1f}{unit}"
    return f"{n:.0f}"


def _mover_line(i: int, q: dict) -> str:
    arrow = "🟢" if (q["change_pct"] or 0) >= 0 else "🔴"
    price = f"${q['close']:.2f}" if q["close"] is not None else "—"
    return (
        f"{RLM}{i}. <b>{html.escape(q['ticker'])}</b> {arrow} "
        f"<b>{q['change_pct']:+.2f}%</b> — السعر {price} — الحجم {_compact(q['volume'])}"
    )


def _section(title: str, movers: list[dict], empty: str) -> list[str]:
    lines = [f"<b>{title}</b>"]
    if movers:
        lines += [_mover_line(i, q) for i, q in enumerate(movers, 1)]
    else:
        lines.append(RLM + empty)
    return lines


def format_morning_message(
    gainers: list[dict], losers: list[dict], asof: Optional[str] = None
) -> str:
    asof = asof or date.today().isoformat()
    lines = [
        "<b>📊 رصد الصباح — الأسهم المتوافقة</b>",
        f"{RLM}📅 {asof} — بعد افتتاح السوق الأمريكي",
        "",
        *_section("🟢 أعلى الرابحين:", gainers, "ما فيه رابحون متوافقون بارزون اليوم."),
        "",
        *_section("🔴 أكبر الخاسرين:", losers, "ما فيه خاسرون متوافقون بارزون اليوم."),
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines)


def format_failure_message(reason: str) -> str:
    return (
        "<b>⚠️ رصد الصباح</b>\n"
        f"{RLM}تعذر تجهيز تقرير اليوم: {html.escape(reason)}\n"
        f"{RLM}بحاول مرة ثانية بكرة، وتقدر تطلب التقرير يدوياً بأي وقت."
    )


def format_urgent_message(
    kind: str, ticker: str, headline: str, why: str, link: Optional[str] = None
) -> str:
    """kind: 'opportunity' for positive news, 'warning' for owned-stock bad news."""
    if kind == "warning":
        head = f"🚨 <b>تنبيه عاجل — سهم تملكه: {html.escape(ticker)}</b>"
    else:
        head = f"⚡️ <b>فرصة محتملة: {html.escape(ticker)}</b>"
    lines = [
        head,
        f"{RLM}📰 {html.escape(headline)}",
        f"{RLM}💡 {html.escape(why)}",
    ]
    if link:
        lines.append(f'{RLM}🔗 <a href="{html.escape(link)}">تفاصيل الخبر</a>')
    lines.append(DISCLAIMER)
    return "\n".join(lines)
