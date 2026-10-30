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

    def test_crossing_marker_is_on_both_interpolated_segments(self):
        prices, averages = [9, 13], [10, 11]
        event, = crossover_events(prices, averages)
        self.assertEqual(event.index, 1)
        self.assertAlmostEqual(event.plot_index, 1/3)
        self.assertAlmostEqual(event.price, 9 + 4/3)
        self.assertAlmostEqual(event.price, 10 + 1/3)
        self.assertEqual(event.price, event.sma)
        self.assertNotEqual(event.price, prices[event.index])

    def test_equal_plateau_places_crossing_at_last_equal_point(self):
        event, = crossover_events([9, 10, 10, 12], [10, 10, 10, 10])
        self.assertEqual((event.index, event.plot_index, event.price), (3, 2, 10))

    def test_c_steadily_rising(self):
        prices = list(range(1, 253))
        for period in [2, 3, 20, 200, 251]:
            self.assertEqual(count_crossings(prices, simple_moving_average(prices, period)), 0)

    def test_d_insufficient_history(self):
        for prices in [[], [1, 2]]:
            with self.assertRaisesRegex(ValueError, "needs at least"):
                simple_moving_average(prices, 3)
            with self.assertRaisesRegex(ValueError, "At least 4"):
                optimize_sma(prices, 12)

    def test_e_equal_to_sma(self):
        prices = [9, 10, 10, 11, 10, 11, 9, 10, 11]
        average = [10] * len(prices)
        self.assertEqual([e.index for e in crossover_events(prices, average)], [3, 8])
        self.assertEqual(count_crossings([10, 10, 11], [10, 10, 10]), 0)
        self.assertEqual(count_crossings([10] * 8, [10] * 8), 0)

    def test_f_optimizer_correctness_and_tie_break(self):
        # Independently known counts: N2 -> 2/6 comparisons = 84/year;
        # N3 -> 2/5 = 100.8/year; N4 -> 1/4 = 63/year. Target 60 selects N4.
        prices = [10, 12, 10, 12, 10, 12, 10, 9]
        result = optimize_sma(prices, 60, [2, 3, 4])
        self.assertEqual(result.period, 4)
        self.assertEqual(result.crossing_count, 1)
        self.assertEqual(result.comparisons, 4)
        self.assertEqual(result.actual_annual_frequency, 63)
        self.assertEqual(result.frequency_error, 3)
        # For this alternating series N2 and N4 both give exactly 126/year.
        for candidates in [[4, 2], [2, 4], [4, 2, 4]]:
            self.assertEqual(optimize_sma([10, 12] * 4, 126, candidates).period, 2)

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
        with self.assertRaisesRegex(ValueError, "Insufficient valid history"):
            optimize_sma([1, None, 3, None, 5], 6)

    def test_three_year_target_uses_entire_history(self):
        result = optimize_sma([10, 12] * 378, 12, [2, 20, 200])
        self.assertEqual(result.history_sessions, 756)
        self.assertEqual(result.comparisons, 756 - result.period)
        self.assertEqual(result.target_crossings, 12 * result.comparisons / 252)
        self.assertTrue(any(e.index < 504 for e in result.events))
        self.assertAlmostEqual(result.actual_annual_frequency, result.crossing_count * 252 / result.comparisons)

    def test_caps_and_real_coverage_apply_to_explicit_candidates(self):
        with self.assertRaisesRegex(ValueError, "between 2 and 126"):
            optimize_sma(list(range(252)), 12, [192])
        with self.assertRaisesRegex(ValueError, "504 observable"):
            optimize_sma([1, 2, None] * 336, 12)
