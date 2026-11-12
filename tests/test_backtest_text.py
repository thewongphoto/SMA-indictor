"""Plain-language backtest copy used by the native and web backtest cards (design 2b)."""
from types import SimpleNamespace
from unittest import TestCase

from sma_analyzer.backtest_text import backtest_span, gain_phrase


class BacktestTextTests(TestCase):
    def test_span_uses_real_month_and_year(self):
        report = SimpleNamespace(start=0, end=2)
        dates = ["2023-11-13", "2025-01-02", "2026-11-11"]
        self.assertEqual(backtest_span(None, report, dates), "Nov 2023 – Nov 2026")

    def test_simulated_span_never_claims_calendar_dates(self):
        report = SimpleNamespace(start=0, end=503)
        self.assertEqual(backtest_span(None, report, None), "2.0 simulated years")

    def test_gain_loss_and_no_buys(self):
        self.assertEqual(gain_phrase(1386.2, 1200, "$"), "+$186 gain on $1,200 contributed")
        self.assertEqual(gain_phrase(1080, 1200, "USD "), "−USD 120 loss on USD 1,200 contributed")
        self.assertEqual(gain_phrase(0, 0, "$"), "No buys in this period")
