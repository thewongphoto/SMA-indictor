"""Independent reference checks for the policy now used by the application."""
from fractions import Fraction
import math
from pathlib import Path
import unittest

from experiments.observable_frequency import (
    annual_frequency, best_candidate, evaluate_candidate, observable_comparisons,
    optimize_proposed, proposed_cap,
)
from sma_analyzer.engine import optimize_sma
from sma_analyzer.mock_data import generate_mock_data


class ObservableFrequencyProposalTests(unittest.TestCase):
    def test_cap_examples_and_boundary(self):
        expected = {4: 2, 251: 125, 252: 126, 503: 251, 504: 252, 505: 252,
                    755: 252, 756: 252, 757: 253, 1008: 504, 1260: 756}
        for history, cap in expected.items():
            with self.subTest(history=history):
                self.assertEqual(proposed_cap(history), cap)

    def test_cap_never_shrinks_and_retains_required_exposure(self):
        previous = proposed_cap(4)
        for history in range(5, 1513):
            cap = proposed_cap(history)
            self.assertGreaterEqual(cap, previous)
            self.assertLessEqual(cap - previous, 1)
            if history <= 756:
                self.assertLessEqual(cap, history // 2)
            else:
                self.assertEqual(history - cap, 504)
            previous = cap

    def test_warmup_and_baseline_excluded_from_exposure(self):
        prices = [10, 12, 10, 12, 10, 12]
        for period, crossings, comparisons, rate in [(2, 2, 4, 126), (4, 1, 2, 126), (5, 1, 1, 252)]:
            with self.subTest(period=period):
                result = evaluate_candidate(prices, period, 12)
                self.assertEqual(result.crossing_count, crossings)
                self.assertEqual(result.comparisons, comparisons)
                self.assertEqual(result.frequency, rate)

    def test_36_crossings_over_three_observable_years(self):
        self.assertEqual(annual_frequency(36, 756), 12)
        # Three raw years with SMA 192 are only 564 usable comparisons.
        self.assertEqual(annual_frequency(36, 756 - 192), Fraction(756, 47))

    def test_known_best_candidate_under_complete_policy(self):
        prices = [10, 12, 10, 12, 10, 12, 10, 9]
        result = optimize_proposed(prices, 60)
        self.assertEqual(result.period, 4)
        self.assertEqual(result.crossing_count, 1)
        self.assertEqual(result.comparisons, 4)
        self.assertEqual(result.frequency, 63)
        self.assertEqual(result.frequency_error, 3)

    def test_minimize_annual_error_instead_of_raw_count_error(self):
        prices = [10, 12, 10, 12, 10, 12, 10, 9]
        result = best_candidate(prices, 60, [2, 7])
        self.assertEqual(result.period, 2)
        self.assertEqual(result.frequency, 84)
        self.assertEqual(evaluate_candidate(prices, 7, 60).frequency, 0)
        # Minimizing raw count error would incorrectly prefer SMA 7 here.
        self.assertLess(abs(0 - Fraction(60, 252)), abs(2 - Fraction(60 * 6, 252)))

    def test_ties_choose_shorter_period_independent_of_order(self):
        prices = [10, 12, 10, 12, 10, 12]
        for candidates in [[2, 4], [4, 2], [4, 2, 4]]:
            result = best_candidate(prices, 126, candidates)
            self.assertEqual(result.period, 2)
            self.assertEqual(result.frequency_error, 0)

    def test_missing_prices_exclude_gap_and_rewarmup(self):
        result = evaluate_candidate([10, 12, 10, None, 12, 10, 12], 2, 12)
        self.assertEqual(result.comparisons, 2)
        self.assertEqual([event.index for event in result.events], [6])
        self.assertEqual(result.frequency, 126)

    def test_equal_observations_are_exposure_without_duplicate_crossings(self):
        prices = [9, 10, 10, 11, 10, 11]
        self.assertEqual(observable_comparisons(prices, [10] * 6), 5)
        result = evaluate_candidate([10] * 8, 2, 12)
        self.assertEqual(result.comparisons, 6)
        self.assertEqual(result.crossing_count, 0)

    def test_nonfinite_values_break_exposure(self):
        self.assertEqual(observable_comparisons([9, math.nan, 11, 12], [10] * 4), 1)
        self.assertEqual(observable_comparisons([9, 10, 11, 12], [10, math.inf, 10, 10]), 1)

    def test_insufficient_history_and_missing_coverage_are_reported(self):
        for prices in [[], [1], [1, 2], [1, 2, 3]]:
            with self.assertRaisesRegex(ValueError, "At least 4"):
                optimize_proposed(prices, 12)
        with self.assertRaisesRegex(ValueError, "Insufficient valid history"):
            optimize_proposed([1, 2, None] * 4, 12)
        with self.assertRaisesRegex(ValueError, "No observable"):
            evaluate_candidate([1, None, 3, None], 2, 12)
        with self.assertRaises(ValueError):
            annual_frequency(0, 0)

    def test_invalid_arguments_are_rejected(self):
        for invalid in [0, -1, 1.5, True]:
            with self.assertRaises(ValueError):
                proposed_cap(invalid)
            with self.assertRaises(ValueError):
                optimize_proposed([1, 2, 3, 4], invalid)
        for candidates in [[], [1], [4]]:
            with self.assertRaises(ValueError):
                best_candidate([1, 2, 3, 4], 12, candidates)
        with self.assertRaises(ValueError):
            observable_comparisons([1], [1, 2])
        with self.assertRaises(ValueError):
            observable_comparisons(["bad"], [1])
        with self.assertRaises(ValueError):
            annual_frequency(2, 1)

    def test_all_six_historical_252_session_fixtures(self):
        for counter in ["DEMO-SGX", "DEMO-US"]:
            for scenario in ["Trending", "Oscillating", "Sideways"]:
                dataset = generate_mock_data(counter, scenario, sessions=252)
                original = dataset.prices
                for target in [12, 6, 1]:
                    result = optimize_proposed(dataset.prices, target)
                    self.assertLessEqual(result.period, 126)
                    self.assertGreaterEqual(result.comparisons, 126)
                self.assertEqual(len(dataset.prices), 252)
                self.assertEqual(dataset.prices, original)
                self.assertEqual(dataset, generate_mock_data(counter, scenario, sessions=252))

    def test_app_optimizer_matches_preintegration_reference(self):
        prices = generate_mock_data("DEMO-SGX", "Sideways", sessions=252).prices
        existing = optimize_sma(prices, 12)
        proposed = optimize_proposed(prices, 12)
        self.assertEqual((existing.period, existing.crossing_count, existing.comparisons), (22, 33, 230))
        self.assertEqual(existing.frequency, proposed.frequency)
        self.assertEqual((proposed.period, proposed.crossing_count, proposed.comparisons), (22, 33, 230))
        self.assertEqual(proposed.frequency, Fraction(4158, 115))
        self.assertEqual(optimize_sma(prices, 12), existing)

    def test_app_has_no_import_of_experimental_policy(self):
        # Production must remain independent of the frozen research reference.
        app_root = Path(__file__).resolve().parents[1] / "sma_analyzer"
        import ast
        for path in app_root.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    self.assertFalse(any(n.name.startswith("experiments") for n in node.names))
                elif isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or "").startswith("experiments"))

    def test_production_matches_reference_across_targets_and_boundary_histories(self):
        for history in [252, 503, 504, 505, 755, 756, 757, 1008]:
            prices = generate_mock_data("DEMO-SGX", "Sideways", history).prices
            targets = [12, 6, 1] if history == 252 else [12]
            for target in targets:
                actual = optimize_sma(prices, target)
                reference = optimize_proposed(prices, target)
                self.assertEqual((actual.period, actual.comparisons, actual.frequency),
                                 (reference.period, reference.comparisons, reference.frequency))
                self.assertEqual(actual.sma, reference.sma)
                self.assertEqual(actual.events, reference.events)
