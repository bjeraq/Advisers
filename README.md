# Advisers

Technical-analysis advisers for the stock market. Each adviser reads a
stock's daily price history and gives a **BUY / HOLD / SELL** opinion with a
score from -1 (bearish) to +1 (bullish). A council combines the opinions in a
weighted vote.

It uses only the Python standard library (3.9+), so there is nothing to
install.

## Advisers

| Adviser     | Idea                                                    | Weight |
|-------------|---------------------------------------------------------|--------|
| `trend`     | SMA50 vs SMA200 (golden/death cross) and price vs SMA50 | 2.0    |
| `macd`      | MACD(12,26,9) histogram and fresh crossovers            | 1.5    |
| `rsi`       | RSI(14): oversold means buy, overbought means sell      | 1.0    |
| `bollinger` | Price position inside the 20-day, 2σ Bollinger bands    | 1.0    |

A council score of +0.25 or more is BUY, -0.25 or less is SELL, and anything
in between is HOLD.

## Usage

```bash
# Local CSV (Yahoo Finance or Stooq export format)
python -m advisers --csv examples/sample.csv

# Download from stooq.com (needs internet access)
python -m advisers AAPL MSFT NVDA
```

Example output:

```
examples/sample.csv  2025-02-24  close 130.71
  => HOLD  (score +0.08)
     trend      BUY  +1.00  SMA50=122.11 vs SMA200=105.81 (golden cross), price 130.71
     macd       HOLD +0.13  MACD=2.29 signal=2.11 hist=+0.17
     rsi        SELL -0.87  RSI14=67.4 (neutral)
     bollinger  SELL -0.89  price 130.71 in band [122.27, 131.19]
```

In this example the long-term trend is up, but the price is stretched near
the top of its range, so the council says HOLD.

To use it as a library:

```python
from advisers import load_csv, default_council

verdict = default_council().advise(load_csv("prices.csv"))
print(verdict.action, verdict.score)
for s in verdict.signals:
    print(s.adviser, s.action, s.reason)
```

To add your own adviser, subclass `advisers.Adviser`, implement
`advise(bars) -> Signal`, and pass it to `Council([(adviser, weight), ...])`.

## Tests

```bash
python -m unittest discover -s tests -t .
```

## Disclaimer

This is for educational use only and is not financial advice. The signals are
simple technical heuristics that do not account for fundamentals, news, costs
or risk. Do your own research before trading.
