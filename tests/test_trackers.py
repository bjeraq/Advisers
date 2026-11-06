import time
import unittest

from advisers.dossier import congress_section, whales_section
from advisers.newswatch import normalize, recent, resolve_symbols
from advisers.whales import diff_holdings, names_match, normalize_name


class WhaleNameTests(unittest.TestCase):
    def test_normalize_strips_suffixes(self):
        self.assertEqual(normalize_name("NVIDIA CORP"), "NVIDIA")
        self.assertEqual(normalize_name("Apple Inc."), "APPLE")

    def test_names_match(self):
        self.assertTrue(names_match("NVIDIA CORP", "NVIDIA Corporation"))
        self.assertTrue(names_match("APPLE INC", "Apple Inc."))
        self.assertFalse(names_match("Micron Technology, Inc.", "Microsoft Corporation"))


class WhaleDiffTests(unittest.TestCase):
    def test_diff_categories(self):
        prev = {
            "C1": {"name": "Kept Co", "cusip": "C1", "value": 100, "shares": 100},
            "C2": {"name": "Gone Co", "cusip": "C2", "value": 50, "shares": 10},
            "C3": {"name": "Up Co", "cusip": "C3", "value": 80, "shares": 100},
        }
        cur = {
            "C1": {"name": "Kept Co", "cusip": "C1", "value": 110, "shares": 105},
            "C3": {"name": "Up Co", "cusip": "C3", "value": 200, "shares": 200},
            "C4": {"name": "New Co", "cusip": "C4", "value": 70, "shares": 5},
        }
        ch = diff_holdings(prev, cur)
        self.assertEqual([h["name"] for h in ch["new"]], ["New Co"])
        self.assertEqual([h["name"] for h in ch["exited"]], ["Gone Co"])
        self.assertEqual([h["name"] for h in ch["increased"]], ["Up Co"])
        self.assertEqual(ch["decreased"], [])


class NewsWatchTests(unittest.TestCase):
    def test_recent_window_and_urgency_sort(self):
        now = time.time()
        items = [
            {"id": "a", "title": "old", "published": now - 7200, "urgency": 1},
            {"id": "b", "title": "new normal", "published": now - 60, "urgency": 2},
            {"id": "c", "title": "new urgent", "published": now - 120, "urgency": 1},
        ]
        out = recent(items, minutes=75, now=now)
        self.assertEqual([i["id"] for i in out], ["c", "b"])

    def test_normalize_builds_story_link(self):
        item = {"id": "x", "title": "t", "published": 1, "urgency": 2,
                "storyPath": "/news/abc"}
        self.assertEqual(normalize(item)["link"],
                         "https://www.tradingview.com/news/abc")

    def test_resolve_symbols_defaults(self):
        out = resolve_symbols(["NYSE:X", "zzzz"], "no_such_file.csv")
        self.assertEqual(out, ["NYSE:X", "NASDAQ:ZZZZ"])


class DossierTrackerSectionTests(unittest.TestCase):
    def test_congress_section_filters_and_summarizes(self):
        payload = {"trades": [
            {"date": "2026-10-20", "politician": "أ", "chamber": "شيوخ",
             "ticker": "NVDA", "side": "buy", "amount": "$100K–$250K",
             "source": "efd"},
            {"date": "2026-10-21", "politician": "ب", "chamber": "نواب",
             "ticker": "AAPL", "side": "sell", "amount": "$15K", "source": "x"},
        ]}
        lines = congress_section("NVDA", payload)
        text = "\n".join(lines)
        self.assertIn("شراء", text)
        self.assertNotIn("AAPL", text)
        self.assertIn("1 شراء مقابل 0 بيع", text)

    def test_whales_section_matches_company(self):
        payload = {"whales": [{
            "name": "بافت", "filed": "2026-08-14",
            "top": [{"name": "NVIDIA CORP", "value": 5e9, "pct": 12.0}],
            "changes": {"new": [{"name": "NVIDIA CORP", "value": 5e9}]},
        }]}
        lines = whales_section("NVDA", "NVIDIA Corporation", payload)
        text = "\n".join(lines)
        self.assertIn("بافت", text)
        self.assertIn("أكبر مراكزه", text)
        self.assertIn("جديد", text)

    def test_whales_section_no_match(self):
        payload = {"whales": [{"name": "x", "filed": "", "top": [], "changes": {}}]}
        self.assertIn("لا يظهر", whales_section("ZZ", "Zz Co", payload)[0])


if __name__ == "__main__":
    unittest.main()
