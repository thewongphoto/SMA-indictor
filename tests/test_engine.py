import math
import unittest

from sma_analyzer.engine import count_crossings, crossover_events, optimize_sma, simple_moving_average


class EngineTests(unittest.TestCase):
    def test_a_sma_arithmetic(self):
        self.assertEqual(simple_moving_average([10, 20, 30, 40], 3), [None, None, 20, 30])

    def test_b_predictable_crossings(self):
        prices = [10, 12, 10, 12, 10, 12]
        sma = simple_moving_average(prices, 2)
        self.assertEqual(count_crossings(prices, sma), 2)
        self.assertEqual([e.index for e in crossover_events(prices, sma)], [3, 5])

    def test_c_steadily_rising(self):
        prices = list(range(1, 253))
        for period in [2, 3, 20, 200, 251]:
            self.assertEqual(count_crossings(prices, simple_moving_average(prices, period)), 0)

    def test_d_insufficient_history(self):
        for prices in [[], [1, 2]]:
            with self.assertRaisesRegex(ValueError, "needs at least"):
                simple_moving_average(prices, 3)
            with self.assertRaisesRegex(ValueError, "At least 3"):
                optimize_sma(prices, 12)

    def test_e_equal_to_sma(self):
        prices = [9, 10, 10, 11, 10, 11, 9, 10, 11]
        average = [10] * len(prices)
        self.assertEqual([e.index for e in crossover_events(prices, average)], [3, 8])
        self.assertEqual(count_crossings([10, 10, 11], [10, 10, 10]), 0)
        self.assertEqual(count_crossings([10] * 8, [10] * 8), 0)

    def test_f_optimizer_correctness_and_tie_break(self):
        prices = [10, 12, 10, 12, 10, 12]
        # Whole history = 6/252 years; target 42/year means exactly one event.
        # N=2 -> 2 crossings, N=3 -> 2, N=4 -> 1, N=5 -> 0.
        result = optimize_sma(prices, 42, [2, 3, 4, 5])
        self.assertEqual(result.period, 4)
        self.assertEqual(result.crossing_count, 1)
        self.assertEqual(result.count_error, 0)
        for candidates in [[3, 2], [2, 3], [3, 2, 3]]:
            self.assertEqual(optimize_sma(prices, 84, candidates).period, 2)

    def test_missing_and_nonfinite_values_reset_crossings(self):
        prices = [9, None, 11, 9, math.nan, 11, 9, math.inf, 11, 9, 11]
        self.assertEqual([e.index for e in crossover_events(prices, [10] * len(prices))], [10])
        self.assertEqual(simple_moving_average([2, 4, None, 6, 8], 2), [None, 3, None, None, 7])
        self.assertEqual(count_crossings([9, 11], [10, None]), 0)

    def test_period_one_and_invalid_inputs(self):
        self.assertEqual(simple_moving_average([2, 3], 1), [2, 3])
        for invalid in [0, -1, 2.5, True]:
            with self.assertRaises(ValueError):
                simple_moving_average([1, 2, 3], invalid)
        with self.assertRaises(ValueError):
            count_crossings([1], [1, 2])
        with self.assertRaises(ValueError):
            simple_moving_average([1, "bad"], 2)
        for invalid in [0, -1, True, 1.5]:
            with self.assertRaises(ValueError):
                optimize_sma([1, 2, 3], invalid)
        for candidates in [[], [1], [4]]:
            with self.assertRaises(ValueError):
                optimize_sma([1, 2, 3], 6, candidates)
        with self.assertRaisesRegex(ValueError, "consecutive"):
            optimize_sma([1, None, 3, None, 5], 6)

    def test_three_year_target_uses_entire_history(self):
        result = optimize_sma([10, 12] * 378, 12, [2, 20, 200])
        self.assertEqual(result.history_sessions, 756)
        self.assertEqual(result.target_crossings, 36)
        self.assertAlmostEqual(result.actual_annual_frequency, result.crossing_count / 3)
