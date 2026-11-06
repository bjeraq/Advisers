import unittest
from datetime import date

from advisers.report import (
    DISCLAIMER,
    format_failure_message,
    format_morning_message,
    format_urgent_message,
)
from advisers.scout import is_trading_day


def q(ticker, change):
    return {"ticker": ticker, "change_pct": change, "close": 10.0, "volume": 2e6}


class ReportTests(unittest.TestCase):
    def test_morning_message_contains_movers_and_disclaimer(self):
        msg = format_morning_message([q("AAA", 4.2)], [q("BBB", -3.1)], "2026-11-06")
        for part in ("AAA", "+4.20%", "BBB", "-3.10%", "2026-11-06", DISCLAIMER):
            self.assertIn(part, msg)

    def test_empty_sections_say_so(self):
        msg = format_morning_message([], [], "2026-11-06")
        self.assertIn("ما فيه رابحون", msg)
        self.assertIn("ما فيه خاسرون", msg)

    def test_failure_message_mentions_reason(self):
        self.assertIn("انقطاع", format_failure_message("انقطاع المصدر"))

    def test_urgent_html_is_escaped(self):
        msg = format_urgent_message("warning", "AAA", "a <b> & c", "سبب")
        self.assertIn("a &lt;b&gt; &amp; c", msg)
        self.assertIn("🚨", msg)


class TradingDayTests(unittest.TestCase):
    def test_weekend_is_not_trading_day(self):
        self.assertFalse(is_trading_day(date(2026, 11, 7)))  # Saturday

    def test_listed_holiday_is_not_trading_day(self):
        self.assertFalse(is_trading_day(date(2026, 11, 26)))  # Thanksgiving

    def test_regular_day_is_trading_day(self):
        self.assertTrue(is_trading_day(date(2026, 11, 6)))  # Friday


if __name__ == "__main__":
    unittest.main()
