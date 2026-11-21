import unittest

from advisers.screener import (
    COMPLIANT,
    NON_COMPLIANT,
    REVIEW,
    classify,
    screen_rows,
    summarize,
)

CFG = {
    "min_market_cap_usd": 2e9,
    "max_debt_to_market_cap": 0.30,
    "max_cash_to_market_cap": 0.30,
    "excluded_industries": ["Major Banks", "Casinos/Gaming"],
    "review_industries": ["Restaurants"],
    "excluded_keywords": ["Bank"],
    "review_keywords": ["Hotel"],
}


def quote(**over):
    base = {
        "symbol": "NASDAQ:TEST", "ticker": "TEST", "company": "Test Corp.",
        "exchange": "NASDAQ", "is_primary": True, "sector": "Tech",
        "industry": "Packaged Software", "market_cap": 10e9,
        "total_debt": 1e9, "cash_sti": 1e9, "close": 50.0,
        "change_pct": 1.0, "volume": 1e6,
    }
    base.update(over)
    return base


class ClassifyTests(unittest.TestCase):
    def test_clean_company_is_compliant(self):
        r = classify(quote(), CFG)
        self.assertEqual(r["status"], COMPLIANT)
        self.assertAlmostEqual(r["debt_ratio"], 0.1)

    def test_excluded_industry(self):
        r = classify(quote(industry="Major Banks"), CFG)
        self.assertEqual(r["status"], NON_COMPLIANT)
        self.assertIn("نشاط غير متوافق", r["reasons"])

    def test_excluded_keyword_in_name(self):
        r = classify(quote(company="First Test Bank Corp."), CFG)
        self.assertEqual(r["status"], NON_COMPLIANT)

    def test_high_debt(self):
        r = classify(quote(total_debt=4e9), CFG)
        self.assertEqual(r["status"], NON_COMPLIANT)
        self.assertIn("الديون", r["reasons"])

    def test_high_cash(self):
        r = classify(quote(cash_sti=5e9), CFG)
        self.assertEqual(r["status"], NON_COMPLIANT)

    def test_review_industry(self):
        r = classify(quote(industry="Restaurants"), CFG)
        self.assertEqual(r["status"], REVIEW)

    def test_review_industry_with_bad_ratios_is_non_compliant(self):
        r = classify(quote(industry="Restaurants", total_debt=9e9), CFG)
        self.assertEqual(r["status"], NON_COMPLIANT)

    def test_missing_financials_needs_review(self):
        r = classify(quote(total_debt=None), CFG)
        self.assertEqual(r["status"], REVIEW)
        self.assertIn("ناقصة", r["reasons"])


class ScreenRowsTests(unittest.TestCase):
    def test_scope_and_summary(self):
        rows = [
            quote(),
            quote(ticker="SMALL", market_cap=1e8),          # below size floor
            quote(ticker="PREF", is_primary=False),          # preferred line
            quote(ticker="OTC", exchange="OTC"),             # off-exchange
            quote(ticker="BNK", industry="Major Banks"),
        ]
        results = screen_rows(rows, CFG)
        tickers = {r["ticker"] for r in results}
        self.assertEqual(tickers, {"TEST", "BNK"})
        self.assertIn("المجموع 2", summarize(results))


class OverrideTests(unittest.TestCase):
    def test_manual_override_wins(self):
        cfg = dict(CFG, overrides={"compliant": ["BNK"]})
        r = classify(quote(ticker="BNK", industry="Major Banks"), cfg)
        self.assertEqual(r["status"], COMPLIANT)
        self.assertIn("قرار يدوي", r["reasons"])


if __name__ == "__main__":
    unittest.main()
