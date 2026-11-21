import csv
import json
import os
import tempfile
import unittest

from advisers.dossier import build, financial_section, news_section
from advisers.ledger import FIELDS, append_row


def _write(tmp, name, obj):
    path = os.path.join(tmp, name)
    with open(path, "w") as f:
        json.dump(obj, f)
    return path


class DossierTests(unittest.TestCase):
    def test_build_full_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            bars = {"bars": [
                {"t": 1700000000 + i * 86400, "o": 100 + i, "h": 101 + i,
                 "l": 99 + i, "c": 100 + i * 0.5, "v": 1e6}
                for i in range(220)
            ]}
            fin = {"data": {"price_earnings_ttm": 25.5, "net_margin_ttm": 21.0}}
            news = {"headlines": [
                {"title": "Prophet beats estimates", "published": 1700000000,
                 "provider": "wire", "urgency": 1},
            ]}
            universe = os.path.join(tmp, "u.csv")
            with open(universe, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "ticker", "symbol", "company", "exchange", "sector",
                    "industry", "market_cap", "debt_ratio", "cash_ratio",
                    "status", "reasons", "asof"])
                w.writeheader()
                w.writerow({"ticker": "TEST", "symbol": "NASDAQ:TEST",
                            "company": "Test", "exchange": "NASDAQ",
                            "sector": "Tech", "industry": "Software",
                            "market_cap": "1", "debt_ratio": "0.1",
                            "cash_ratio": "0.2", "status": "compliant",
                            "reasons": "ok", "asof": "2026-01-01"})
            text = build(
                "TEST",
                _write(tmp, "b.json", bars),
                _write(tmp, "f.json", fin),
                _write(tmp, "n.json", news),
                universe,
            )
        for part in ("ملف الحقائق — TEST", "متوافق", "آخر إغلاق",
                     "مكرر الربحية: 25.50", "Prophet beats estimates",
                     "المتوسطات"):
            self.assertIn(part, text)

    def test_missing_inputs_are_graceful(self):
        text = build("GHOST", None, None, None, None)
        self.assertIn("لا توجد قائمة فحص", text)
        self.assertIn("غير كافية", text)
        self.assertIn("لم تُجلب", text)

    def test_financial_section_flattens_nested(self):
        lines = financial_section({"x": {"revenue_ttm": 2e9}})
        self.assertIn("- الإيرادات السنوية: 2.00B", lines)

    def test_news_section_limit(self):
        items = [{"title": f"t{i}", "published": 1700000000} for i in range(20)]
        self.assertEqual(len(news_section(items, limit=5)), 5)


class LedgerTests(unittest.TestCase):
    def test_append_creates_header_and_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "led", "rec.csv")
            append_row("nvda", "full", 181.6, {"الفني": 4}, "انتظار", "r.md",
                       ledger_path=path)
            append_row("AAPL", "quick", None, {}, "شراء جزئي", "r2.md",
                       ledger_path=path)
            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["ticker"], "NVDA")
        self.assertEqual(rows[0]["price"], "181.60")
        self.assertIn("الفني", rows[0]["scores_json"])
        self.assertEqual(list(rows[0]), FIELDS)


if __name__ == "__main__":
    unittest.main()
