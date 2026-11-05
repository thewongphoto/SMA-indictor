from datetime import date,timedelta
import unittest

from sma_analyzer.axis import date_ticks
from sma_analyzer.viewport import ChartViewport
from sma_analyzer.backtest import InvestmentScenario
from sma_analyzer.presentation import display_text,endpoint_label


class CalendarAxisTests(unittest.TestCase):
    def setUp(self):
        self.dates = tuple((date(2000,1,1)+timedelta(days=i)).isoformat() for i in range(10000))

    def ticks(self,start,end,width):
        return date_ticks(self.dates,start,end,width,lambda text:len(text)*7,gap=12)

    def test_month_labels_skip_and_switch_to_years(self):
        months = self.ticks(0,365,350)
        self.assertGreaterEqual(len(months),2)
        self.assertTrue(all("2000" in tick.label for tick in months))
        self.assertTrue(all(" " in tick.label for tick in months))
        self.assertTrue(all(" " in tick.label for tick in self.ticks(0,1095,1000)))
        years = self.ticks(0,9999,350)
        self.assertGreaterEqual(len(years),2)
        self.assertTrue(all(tick.label.isdigit() for tick in years))
        self.assertLess(len(years),28)

    def test_labels_never_overlap_at_mobile_widths_and_fractional_zoom(self):
        for width in (40,70,120,220,350,900):
            for start,end in ((0,365),(244.3,302.8),(0,9999),(570.1,571.3)):
                ticks = self.ticks(start,end,width)
                for tick in ticks:
                    self.assertGreaterEqual(tick.center-tick.width/2,-1e-7)
                    self.assertLessEqual(tick.center+tick.width/2,width+1e-7)
                for left,right in zip(ticks,ticks[1:]):
                    self.assertGreaterEqual(right.center-right.width/2,left.center+left.width/2+12)

    def test_fractional_pinch_moves_without_whole_session_jumps(self):
        view = ChartViewport(500)
        initial = view.bounds
        spans = []
        for scale in (1.0001,1.0002,1.0003):
            view.pinch(initial,249.5,.5,scale)
            spans.append(view.end-view.start)
            self.assertIsNotNone(view.y_limits(tuple(range(500))))
        self.assertTrue(all(0<left-right<.1 for left,right in zip(spans,spans[1:])))
        self.assertTrue(any(value!=round(value) for value in view.bounds))

    def test_returns_use_contributions_and_zero_buys_have_no_return(self):
        self.assertAlmostEqual(InvestmentScenario((1,2),220).return_percent,10)
        self.assertAlmostEqual(InvestmentScenario((1,2),180).return_percent,-10)
        self.assertIsNone(InvestmentScenario((),0).return_percent)

    def test_visible_diagnostics_use_service_labels(self):
        self.assertEqual(endpoint_label("https://query1.finance.yahoo.com/v8/finance/chart/AAPL"),
                         "Daily closes · AAPL")
        for value in ("Yahoo Finance 403 Forbidden","Yahoo HTTPS JSON","YAHOO:AAPL · Yahoo EOD"):
            self.assertNotIn("yahoo",display_text(value).lower())
