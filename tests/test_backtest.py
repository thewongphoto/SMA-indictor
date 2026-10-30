import math
import random
import unittest
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP

from sma_analyzer.backtest import (InvestmentScenario, compare_investments,
                                   equal_period_indices, modal_random_sample, period_sessions)
from sma_analyzer.engine import Crossover, crossover_events
from sma_analyzer.mock_data import Dataset


class BacktestTests(unittest.TestCase):
    def test_crossing_fill_and_equal_budgets(self):
        prices = (10, 10, 20, 10, 40)
        sma = (None, 11, 15, 15, 25)
        events = crossover_events(prices, sma)
        report = compare_investments(prices, sma, events, 5)
        self.assertEqual(report.crossings.indices, (2, 4))
        self.assertAlmostEqual(report.crossings.ending_value, 4000/7)
        self.assertEqual(report.dca.indices, (0, 2))
        self.assertEqual(report.dca.ending_value, 600)
        for scenario in (report.crossings, report.random, report.dca):
            self.assertEqual(scenario.invested, 200)
            self.assertEqual(len(set(scenario.indices)), 2)
            self.assertAlmostEqual(scenario.ending_value, sum(100 * 40 / p for p in scenario.entry_prices))
        self.assertEqual(compare_investments(prices, sma, events, 5), report)

    def test_rolling_period_uses_existing_crossing_price(self):
        prices = (10, 10, 20, 10, 40)
        sma = (None, 11, 15, 15, 25)
        report = compare_investments(prices, sma, crossover_events(prices, sma), 2)
        self.assertEqual((report.start, report.end), (3, 4))
        self.assertEqual(report.crossings.indices, (4,))
        self.assertAlmostEqual(report.crossings.ending_value, 4000/17.5)
        self.assertEqual(report.dca.indices, (3,))  # User confirmed N=1 starts at the period start.
        self.assertEqual(report.dca.ending_value, 400)
        self.assertTrue(set(report.random.indices) <= {3, 4})

    def test_dca_schedule_starts_each_equal_trading_period(self):
        eligible = list(range(1008, 1260))
        self.assertEqual(equal_period_indices(1008, 1259, 1, eligible), (1008,))
        self.assertEqual(equal_period_indices(1008, 1259, 2, eligible), (1008, 1134))
        self.assertEqual(equal_period_indices(1008, 1259, 3, eligible), (1008, 1092, 1176))
        self.assertEqual(equal_period_indices(0, 4, 5, list(range(5))), tuple(range(5)))
        self.assertEqual(equal_period_indices(0, 4, 0, list(range(5))), ())
        self.assertEqual(equal_period_indices(0, 5, 3, [1, 3, 5]), (1, 3, 5))

    def test_500_seed_ensemble_mode_and_percentile_match_independent_reference(self):
        prices = (10, 11, 20, 30, 40, 50)
        events = (Crossover(2, 15, 15, 1.5), Crossover(4, 35, 35, 3.5))
        report = compare_investments(prices, (10,) * 6, events, 6)
        samples = [tuple(sorted(random.Random(seed).sample(range(6), 2))) for seed in range(500)]
        averages = tuple(sum(prices[i] for i in sample)/2 for sample in samples)
        self.assertEqual(report.random_average_prices, averages)
        self.assertEqual(len(averages), 500)
        counts = Counter(int(Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)) for value in averages)
        mode = report.random_mode
        self.assertEqual(counts[mode.rounded_price], max(counts.values()))
        self.assertEqual(mode.frequency, counts[mode.rounded_price])
        self.assertEqual(report.random.indices, samples[mode.seed])
        self.assertAlmostEqual(report.random.ending_value, sum(5000/prices[i] for i in samples[mode.seed]))
        self.assertEqual(report.outperformance_percent, 100 * sum(value > 25 for value in averages)/500)

    def test_dollar_mode_rounding_and_deterministic_ties(self):
        mode = modal_random_sample((10.49, 10.50, 11.2, 12.49))
        self.assertEqual((mode.rounded_price, mode.frequency, mode.seed), (11, 2, 2))
        self.assertEqual(modal_random_sample((10.0, 12.0)).rounded_price, 10)
        self.assertEqual(modal_random_sample((10.0,) * 500).seed, 0)

    def test_percentile_excludes_ties_and_is_based_on_mean_prices(self):
        report = compare_investments((10, 20), (10, 10), [Crossover(1, 10, 10, .5)], 2)
        higher = sum(value == 20 for value in report.random_average_prices)
        self.assertEqual(report.outperformance_percent, 100*higher/500)
        self.assertNotEqual(report.outperformance_percent, 100)
        # Equal-dollar purchases mean arithmetic price rank need not equal portfolio rank.
        report = compare_investments((1, 100, 2, 2), (2, 2, 2, 2),
                                     [Crossover(2, 2, 2, 1.5), Crossover(3, 2, 2, 2.5)], 4)
        self.assertEqual(report.crossings.average_price, 2)
        self.assertEqual(report.outperformance_percent,
                         100*sum(value > 2 for value in report.random_average_prices)/500)

    def test_missing_closes_excluded_but_dca_and_random_can_buy_during_sma_warmup(self):
        prices = (10, None, 11, 12, 13, 14, 15)
        sma = (None, None, None, 11, 12, 13, 14)
        report = compare_investments(prices, sma, [Crossover(4, 12.5, 12.5, 3.5)], 7)
        self.assertEqual(report.eligible_sessions, 6)
        self.assertEqual(report.dca.indices, (0,))
        self.assertTrue(set(report.random.indices) <= {0, 2, 3, 4, 5, 6})
        with self.assertRaisesRegex(ValueError, 'final EOD'):
            compare_investments((1, 2, None), (1, 1, 1), [], 3)

    def test_no_crossings_means_no_money_and_no_defined_percentile(self):
        report = compare_investments((10, 9, 8), (10, 10, 10), [], 3)
        for scenario in (report.crossings, report.random, report.dca):
            self.assertEqual((scenario.indices, scenario.ending_value, scenario.invested), ((), 0, 0))
        self.assertIsNone(report.outperformance_percent)
        self.assertIsNone(report.random_mode)

    def test_ending_value_difference_is_relative_to_scenario_a(self):
        baseline = InvestmentScenario((1,), 110)
        self.assertEqual(InvestmentScenario((2,), 121).difference_percent(baseline), 10)
        self.assertEqual(InvestmentScenario((2,), 99).difference_percent(baseline), -10)
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
