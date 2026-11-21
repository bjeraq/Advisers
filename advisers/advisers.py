"""Advisers turn price history into BUY / HOLD / SELL opinions.

Every adviser returns a Signal with a score in [-1, 1]: positive leans
bullish, negative bearish. A Council averages its members' scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import indicators as ind
from .data import Bar

BUY, HOLD, SELL = "BUY", "HOLD", "SELL"


def _clamp(x: float) -> float:
    return max(-1.0, min(1.0, x))


def action_for(score: float, threshold: float = 0.25) -> str:
    if score >= threshold:
        return BUY
    if score <= -threshold:
        return SELL
    return HOLD


@dataclass
class Signal:
    adviser: str
    score: float
    reason: str
    action: str = field(init=False)

    def __post_init__(self) -> None:
        self.score = _clamp(self.score)
        self.action = action_for(self.score)


class Adviser:
    name = "adviser"

    def advise(self, bars: list[Bar]) -> Signal:
        raise NotImplementedError

    def _not_enough(self, needed: int, have: int) -> Signal:
        return Signal(self.name, 0.0, f"needs {needed} bars, have {have}")


class TrendAdviser(Adviser):
    """Price vs. short and long simple moving averages (golden/death cross)."""

    name = "trend"

    def __init__(self, short: int = 50, long: int = 200):
        self.short, self.long = short, long

    def advise(self, bars: list[Bar]) -> Signal:
        closes = [b.close for b in bars]
        if len(closes) < self.long:
            return self._not_enough(self.long, len(closes))
        s = ind.sma(closes, self.short)[-1]
        l = ind.sma(closes, self.long)[-1]
        price = closes[-1]
        score = 0.5 if s > l else -0.5
        score += 0.5 if price > s else -0.5
        cross = "golden cross" if s > l else "death cross"
        return Signal(
            self.name,
            score,
            f"SMA{self.short}={s:.2f} vs SMA{self.long}={l:.2f} ({cross}), price {price:.2f}",
        )


class RSIAdviser(Adviser):
    """Contrarian: oversold RSI is a buy, overbought is a sell."""

    name = "rsi"

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period, self.oversold, self.overbought = period, oversold, overbought

    def advise(self, bars: list[Bar]) -> Signal:
        closes = [b.close for b in bars]
        value = ind.rsi(closes, self.period)[-1]
        if value is None:
            return self._not_enough(self.period + 1, len(closes))
        mid = (self.oversold + self.overbought) / 2
        half = (self.overbought - self.oversold) / 2
        score = (mid - value) / half
        state = (
            "oversold" if value <= self.oversold
            else "overbought" if value >= self.overbought
            else "neutral"
        )
        return Signal(self.name, score, f"RSI{self.period}={value:.1f} ({state})")


class MACDAdviser(Adviser):
    """MACD histogram direction and size relative to price."""

    name = "macd"

    def advise(self, bars: list[Bar]) -> Signal:
        closes = [b.close for b in bars]
        line, sig, hist = ind.macd(closes)
        if hist[-1] is None:
            return self._not_enough(35, len(closes))
        h = hist[-1]
        prev = hist[-2] if len(hist) > 1 and hist[-2] is not None else h
        # Normalise by 1% of price so the score is comparable across tickers.
        score = h / (closes[-1] * 0.01)
        if (prev <= 0 < h) or (prev >= 0 > h):
            score += 0.5 if h > 0 else -0.5
        return Signal(
            self.name,
            score,
            f"MACD={line[-1]:.2f} signal={sig[-1]:.2f} hist={h:+.2f}",
        )


class BollingerAdviser(Adviser):
    """Contrarian: near the lower band is a buy, near the upper is a sell."""

    name = "bollinger"

    def __init__(self, period: int = 20, width: float = 2.0):
        self.period, self.width = period, width

    def advise(self, bars: list[Bar]) -> Signal:
        closes = [b.close for b in bars]
        lower, mid, upper = ind.bollinger(closes, self.period, self.width)
        if mid[-1] is None:
            return self._not_enough(self.period, len(closes))
        price = closes[-1]
        half = (upper[-1] - lower[-1]) / 2
        score = 0.0 if half == 0 else (mid[-1] - price) / half
        return Signal(
            self.name,
            score,
            f"price {price:.2f} in band [{lower[-1]:.2f}, {upper[-1]:.2f}]",
        )


@dataclass
class Verdict:
    score: float
    action: str
    signals: list[Signal]


class Council:
    """Weighted vote of several advisers."""

    def __init__(self, members: list[tuple[Adviser, float]]):
        self.members = members

    def advise(self, bars: list[Bar]) -> Verdict:
        signals = [a.advise(bars) for a, _ in self.members]
        total_w = sum(w for _, w in self.members) or 1.0
        score = sum(s.score * w for s, (_, w) in zip(signals, self.members)) / total_w
        return Verdict(score, action_for(score), signals)


def default_council() -> Council:
    return Council(
        [
            (TrendAdviser(), 2.0),
            (MACDAdviser(), 1.5),
            (RSIAdviser(), 1.0),
            (BollingerAdviser(), 1.0),
        ]
    )
