import os
import unittest

from advisers import (
    Signal,
    BollingerAdviser,
    RSIAdviser,
    TrendAdviser,
    default_council,
    load_csv,
)
from advisers.advisers import BUY, HOLD, SELL
from tests.helpers import bars_from_closes

EXAMPLE = os.path.join(os.path.dirname(__file__), "..", "examples", "sample.csv")


class AdviserTests(unittest.TestCase):
    def test_signal_score_is_clamped(self):
        self.assertEqual(Signal("x", 5.0, "").score, 1.0)
        self.assertEqual(Signal("x", -0.1, "").action, HOLD)

    def test_trend_uptrend_buys(self):
        bars = bars_from_closes([100 + i for i in range(250)])
        self.assertEqual(TrendAdviser().advise(bars).action, BUY)

    def test_trend_downtrend_sells(self):
        bars = bars_from_closes([400 - i for i in range(250)])
        self.assertEqual(TrendAdviser().advise(bars).action, SELL)

    def test_short_history_holds(self):
        sig = TrendAdviser().advise(bars_from_closes([1, 2, 3]))
        self.assertEqual((sig.action, sig.score), (HOLD, 0.0))
        self.assertIn("needs", sig.reason)

    def test_rsi_is_contrarian(self):
        up = bars_from_closes([100 + i for i in range(30)])
        self.assertEqual(RSIAdviser().advise(up).action, SELL)

    def test_bollinger_below_band_buys(self):
        bars = bars_from_closes([100, 101] * 15 + [90])
        self.assertEqual(BollingerAdviser().advise(bars).action, BUY)

    def test_council_on_sample_csv(self):
        bars = load_csv(EXAMPLE)
        self.assertGreater(len(bars), 200)
        verdict = default_council().advise(bars)
        self.assertIn(verdict.action, (BUY, HOLD, SELL))
        self.assertEqual(len(verdict.signals), 4)
        self.assertTrue(-1 <= verdict.score <= 1)


if __name__ == "__main__":
    unittest.main()
