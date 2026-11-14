"""Technical indicators over plain lists of floats.

Each function returns a list the same length as its input, with None where
there is not yet enough history to compute a value.
"""

from __future__ import annotations

from math import sqrt
from typing import Optional

Series = list[Optional[float]]


def sma(values: list[float], period: int) -> Series:
    out: Series = [None] * len(values)
    total = 0.0
    for i, v in enumerate(values):
        total += v
        if i >= period:
            total -= values[i - period]
        if i >= period - 1:
            out[i] = total / period
    return out


def ema(values: list[float], period: int) -> Series:
    out: Series = [None] * len(values)
    if len(values) < period:
        return out
    k = 2 / (period + 1)
    prev = sum(values[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(values: list[float], period: int = 14) -> Series:
    """Wilder's Relative Strength Index (0-100)."""
    out: Series = [None] * len(values)
    if len(values) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains += max(change, 0)
        losses += max(-change, 0)
    avg_gain, avg_loss = gains / period, losses / period

    def value(g: float, l: float) -> float:
        if l == 0:
            return 100.0 if g > 0 else 50.0
        return 100 - 100 / (1 + g / l)

    out[period] = value(avg_gain, avg_loss)
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0)) / period
        out[i] = value(avg_gain, avg_loss)
    return out


def macd(
    values: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[Series, Series, Series]:
    """Return (macd line, signal line, histogram)."""
    fast_ema, slow_ema = ema(values, fast), ema(values, slow)
    line: Series = [
        f - s if f is not None and s is not None else None
        for f, s in zip(fast_ema, slow_ema)
    ]
    start = next((i for i, v in enumerate(line) if v is not None), len(line))
    sig_tail = ema([v for v in line[start:]], signal)  # type: ignore[misc]
    sig: Series = [None] * start + sig_tail
    hist: Series = [
        m - s if m is not None and s is not None else None for m, s in zip(line, sig)
    ]
    return line, sig, hist


def bollinger(
    values: list[float], period: int = 20, width: float = 2.0
) -> tuple[Series, Series, Series]:
    """Return (lower band, middle band, upper band)."""
    mid = sma(values, period)
    lower: Series = [None] * len(values)
    upper: Series = [None] * len(values)
    for i, m in enumerate(mid):
        if m is None:
            continue
        window = values[i - period + 1 : i + 1]
        sd = sqrt(sum((v - m) ** 2 for v in window) / period)
        lower[i], upper[i] = m - width * sd, m + width * sd
    return lower, mid, upper
