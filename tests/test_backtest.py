import unittest
from types import SimpleNamespace

from sma_analyzer.backtest import InvestmentScenario, compare_investments, period_sessions
from sma_analyzer.engine import crossover_events
from sma_analyzer.mock_data import Dataset


class BacktestTests(unittest.TestCase):
    def test_equal_budgets_and_close_to_final_value(self):
        prices = (10, 10, 20, 10, 40)
        sma = (None, 11, 15, 15, 25)
        events = crossover_events(prices, sma)
        report = compare_investments(prices, sma, events, 5)
        self.assertEqual(report.crossings.indices, (2, 4))
        self.assertEqual(report.crossings.ending_value, 300)
        self.assertEqual(report.highest.indices, (4, 2))  # 300%, then 100%.
        for scenario in (report.crossings, report.random, report.highest):
            self.assertEqual(scenario.invested, 200)
            self.assertEqual(len(set(scenario.indices)), 2)
            self.assertAlmostEqual(scenario.ending_value, sum(100 * 40 / prices[i] for i in scenario.indices))
        self.assertEqual(compare_investments(prices, sma, events, 5), report)

    def test_rolling_period_retains_full_history_sma_and_previous_close(self):
        prices = (10, 10, 20, 10, 40)
        sma = (None, 11, 15, 15, 25)
        report = compare_investments(prices, sma, crossover_events(prices, sma), 2)
        self.assertEqual((report.start, report.end), (3, 4))
        self.assertEqual(report.crossings.indices, (4,))
        self.assertEqual(report.highest.indices, (4,))
        self.assertEqual(report.crossings.ending_value, 100)
        self.assertTrue(set(report.random.indices) <= {3, 4})

    def test_daily_percentage_ranking_not_absolute_price_or_gain(self):
        prices = (1, 2, 100, 110, 50, 75)
        sma = (1,) * len(prices)
        report = compare_investments(prices, sma, [SimpleNamespace(index=1), SimpleNamespace(index=3)], 6)
        self.assertEqual(report.highest.indices, (2, 1))
        self.assertEqual(report.highest.ending_value, 75 + 3750)

    def test_missing_data_and_warmup_excluded_for_every_scenario(self):
        prices = (10, None, 11, 12, 13, 14, 15)
        sma = (None, None, None, 11, 12, 13, 14)
        report = compare_investments(prices, sma, [SimpleNamespace(index=4), SimpleNamespace(index=1)], 7)
        self.assertEqual(report.eligible_sessions, 3)
        self.assertEqual(report.crossings.indices, (4,))
        self.assertTrue(set(report.random.indices) <= {4, 5, 6})
        with self.assertRaisesRegex(ValueError, 'final EOD'):
            compare_investments((1, 2, None), (1, 1, 1), [], 3)

    def test_no_crossings_means_no_money_in_any_scenario(self):
        report = compare_investments((10, 9, 8), (10, 10, 10), [], 3)
        for scenario in (report.crossings, report.random, report.highest):
            self.assertEqual((scenario.indices, scenario.ending_value, scenario.invested), ((), 0, 0))

    def test_few_positive_days_still_uses_equal_budget_and_reports_it(self):
        report = compare_investments((10, 9, 8), (8, 8, 8), [SimpleNamespace(index=2)], 3)
        self.assertEqual(report.highest.indices, (1,))
        self.assertEqual(report.positive_ranked_days, 0)
        self.assertEqual(report.highest.invested, report.crossings.invested)

    def test_ending_value_difference_is_relative_to_scenario_a(self):
        baseline = InvestmentScenario((1,), 110)
        self.assertEqual(InvestmentScenario((2,), 121).difference_percent(baseline), 10)
        self.assertEqual(InvestmentScenario((2,), 99).difference_percent(baseline), -10)
        self.assertEqual(baseline.difference_percent(baseline), 0)
        self.assertIsNone(baseline.difference_percent(InvestmentScenario((), 0)))

    def test_periods_custom_validation_and_clamping(self):
        self.assertEqual(period_sessions('3Y', '', 1260), 756)
        self.assertEqual(period_sessions('Max', '', 500), 500)
        self.assertEqual(period_sessions('5Y', '', 500), 500)
        self.assertEqual(period_sessions('Custom', '1.5', 1260), 378)
        for text in ('', 'nan', 'inf', '-1', '0', '0.001', 'abc', '101'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                period_sessions('Custom', text, 1260)

    def test_simulated_dates_are_stable_weekdays_with_explicit_label(self):
        data = Dataset('DEMO-SGX', 'Trending', (1,) * 7)
        self.assertEqual(data.dates[0], '2021-01-04')
        self.assertEqual(data.dates[4:6], ('2021-01-08', '2021-01-11'))
        self.assertIn('SIMULATED', data.label)
