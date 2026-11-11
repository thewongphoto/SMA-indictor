from unittest import TestCase

from sma_analyzer.chart_comparison import comparison_period, currency_prefix, visible_price_change


class ChartComparisonTests(TestCase):
    def test_change_is_end_minus_start_and_percent_uses_start_close(self):
        increase = visible_price_change((100, 105, 110), (0, 2))
        self.assertEqual((increase.change, increase.percent, increase.direction), (10, 10, "up"))
        decrease = visible_price_change((100, 95, 90), (0, 2))
        self.assertEqual((decrease.change, decrease.percent, decrease.direction), (-10, -10, "down"))

    def test_fractional_pinch_only_compares_eod_points_inside_the_plot(self):
        # The renderer clips the interpolated edges; prices 0 and 4 are outside.
        change = visible_price_change((1000, 20, 25, 30, 2000), (.2, 3.8))
        self.assertEqual((change.first, change.last, change.change, change.percent), (1, 3, 10, 50))

    def test_missing_edges_do_not_borrow_a_price_outside_the_view(self):
        prices = (100, None, float("nan"), 30, 36, float("inf"), None, 200)
        change = visible_price_change(prices, (1, 6))
        self.assertEqual((change.first, change.last, change.change, change.percent), (3, 4, 6, 20))
        self.assertIsNone(visible_price_change(prices, (1, 2)))

    def test_flat_single_zero_and_empty_ranges_have_defined_results(self):
        for prices, bounds in (((5, 5), (0, 1)), ((5,), (0, 0))):
            change = visible_price_change(prices, bounds)
            self.assertEqual((change.change, change.percent, change.direction), (0, 0, "flat"))
        self.assertIsNone(visible_price_change((), (0, 0)))
        self.assertIsNone(visible_price_change((1, 2), (.1, .9)))
        self.assertIsNone(visible_price_change((1, 2), (float("nan"), 1)))
        self.assertIsNone(visible_price_change((0, 5), (0, 1)).percent)

    def test_presets_and_pinches_have_distinct_period_labels(self):
        dates = ("2026-05-29", "2026-06-01", "2026-11-10")
        change = visible_price_change((100, 110, 130), (.2, 2))
        self.assertEqual(comparison_period(change, dates, "6M", False), "PAST 6M")
        self.assertEqual(comparison_period(change, dates, "6M", True), "01 Jun '26 - 10 Nov '26")
        self.assertEqual(comparison_period(None, (), "Max", False), "PAST MAX")
        self.assertEqual(comparison_period(None, (), "1Y", True), "VISIBLE RANGE")

    def test_quote_currency_does_not_imply_a_currency_conversion(self):
        self.assertEqual(currency_prefix("USD"), "US$")
        self.assertEqual(currency_prefix("SGD"), "S$")
        self.assertEqual(currency_prefix("JPY"), "JPY ")
