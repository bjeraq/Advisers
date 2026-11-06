import unittest

from advisers.movers import top_movers

UNIVERSE = {
    "AAA": {"status": "compliant"},
    "BBB": {"status": "compliant"},
    "CCC": {"status": "compliant"},
    "BNK": {"status": "non_compliant"},
    "REV": {"status": "review"},
}


def q(ticker, change, close=100.0, volume=1e6, company=None):
    return {
        "symbol": f"NASDAQ:{ticker}", "ticker": ticker,
        "company": company or f"{ticker} Inc.", "exchange": "NASDAQ",
        "is_primary": True, "sector": "", "industry": "",
        "market_cap": 1e10, "total_debt": None, "cash_sti": None,
        "close": close, "change_pct": change, "volume": volume,
    }


class MoversTests(unittest.TestCase):
    def test_only_compliant_tickers_rank(self):
        rows = [q("AAA", 5), q("BNK", 9), q("REV", 8), q("BBB", -4)]
        gainers, losers = top_movers(rows, UNIVERSE)
        self.assertEqual([g["ticker"] for g in gainers], ["AAA"])
        self.assertEqual([l["ticker"] for l in losers], ["BBB"])

    def test_illiquid_rows_dropped(self):
        rows = [q("AAA", 5), q("BBB", 7, close=1.0, volume=100)]
        gainers, _ = top_movers(rows, UNIVERSE)
        self.assertEqual([g["ticker"] for g in gainers], ["AAA"])

    def test_share_classes_merge_keeping_most_liquid(self):
        rows = [
            q("AAA", 5, volume=9e6, company="Alpha Inc."),
            q("BBB", 5, volume=1e6, company="Alpha Inc. - Class B"),
            q("CCC", 2),
        ]
        gainers, _ = top_movers(rows, UNIVERSE, top=5)
        self.assertEqual([g["ticker"] for g in gainers], ["AAA", "CCC"])

    def test_top_n_cut(self):
        rows = [q("AAA", 1), q("BBB", 2), q("CCC", 3)]
        gainers, _ = top_movers(rows, UNIVERSE, top=2)
        self.assertEqual([g["ticker"] for g in gainers], ["CCC", "BBB"])


if __name__ == "__main__":
    unittest.main()
