import unittest

from advisers import indicators as ind


class IndicatorTests(unittest.TestCase):
    def test_sma(self):
        self.assertEqual(ind.sma([1, 2, 3, 4, 5], 3), [None, None, 2.0, 3.0, 4.0])

    def test_ema_seeds_with_sma(self):
        out = ind.ema([1, 2, 3, 4], 3)
        self.assertEqual(out[:3], [None, None, 2.0])
        self.assertAlmostEqual(out[3], 3.0)

    def test_rsi_extremes(self):
        self.assertEqual(ind.rsi(list(range(1, 30)))[-1], 100.0)
        self.assertEqual(ind.rsi(list(range(30, 1, -1)))[-1], 0.0)
        self.assertEqual(ind.rsi([5.0] * 30)[-1], 50.0)

    def test_macd_lengths_and_sign(self):
        values = [float(i) for i in range(60)]
        line, sig, hist = ind.macd(values)
        self.assertEqual(len(line), len(sig), len(hist))
        self.assertIsNone(hist[30])
        self.assertGreater(line[-1], 0)

    def test_bollinger_flat_series(self):
        lower, mid, upper = ind.bollinger([10.0] * 25)
        self.assertEqual((lower[-1], mid[-1], upper[-1]), (10.0, 10.0, 10.0))


if __name__ == "__main__":
    unittest.main()
