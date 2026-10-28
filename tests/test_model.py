from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sma_analyzer.engine import crossover_events, optimize_sma, simple_moving_average
from sma_analyzer.mock_data import Dataset, generate_mock_data
from sma_analyzer.model import AnalyzerModel
from sma_analyzer.settings import COUNTERS, SCENARIOS
from sma_analyzer.storage import LineStore


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "lines.sqlite3"
        self.model = AnalyzerModel(LineStore(self.path))

    def test_g_frequency_controls_update_optimizer_and_display(self):
        for frequency in [12, 6, 1, 9]:
            self.model.set_target(str(frequency))
            self.assertIsNone(self.model.result)
            result = self.model.calculate()
            self.assertAlmostEqual(result.target_crossings, frequency * result.comparisons / 252)
            self.assertEqual(result.target_frequency, frequency)
            self.assertEqual(self.model.summary()["target"], f"{frequency} / yr")
            self.assertEqual(self.model.summary()["count"], str(result.crossing_count))

    def test_chart_and_table_use_engine_values(self):
        result = self.model.calculate()
        self.assertEqual(self.model.plot_lines()[0].sma,
                         tuple(simple_moving_average(self.model.dataset.prices, result.period)))
        events = crossover_events(self.model.dataset.prices, result.sma)
        self.assertEqual(result.events, events)
        self.assertEqual(self.model.event_rows(), [
            (f"{e.index + 1:03d}", f"{e.price:.4f}", f"{e.sma:.4f}") for e in events])

    def test_scenario_and_counter_selection_refresh_data(self):
        seen = set()
        for counter in COUNTERS:
            for scenario in SCENARIOS:
                self.model.select_dataset(counter, scenario)
                self.assertIsNone(self.model.result)
                data = self.model.dataset
                self.assertEqual(len(data.prices), 1260)
                self.assertIn("SIMULATED", data.label)
                seen.add(data.prices)
                self.assertEqual(data, generate_mock_data(counter, scenario))
                result = self.model.calculate()
                self.assertEqual(result, optimize_sma(data.prices, self.model.target_frequency))
        self.assertEqual(len(seen), 6)

    def test_local_save_deduplication_scope_visibility_and_delete(self):
        result = self.model.calculate()
        self.model.save_current()
        self.model.save_current()
        restored = AnalyzerModel(LineStore(self.path))
        saved, = restored.saved_lines()
        self.assertEqual(saved.period, result.period)
        self.assertEqual(len(restored.plot_lines()), 1)
        restored.store.set_visible(saved.id, False)
        self.assertEqual(restored.plot_lines(), [])
        self.assertFalse(AnalyzerModel(LineStore(self.path)).saved_lines()[0].visible)
        restored.store.set_visible(saved.id, True)
        restored.select_dataset("DEMO-US", "Oscillating")
        self.assertEqual(restored.saved_lines(), [])
        restored.select_dataset("DEMO-SGX", "Oscillating")
        self.assertEqual(len(restored.plot_lines()), 1)
        restored.store.delete(saved.id)
        self.assertEqual(restored.saved_lines(), [])

    def test_active_hide_takes_precedence_over_duplicate_saved_period(self):
        self.model.calculate()
        self.model.save_current()
        self.assertEqual(len(self.model.plot_lines()), 1)
        self.model.active_visible = False
        self.assertEqual(self.model.plot_lines(), [])

    def test_invalid_target_and_empty_data_have_helpful_errors(self):
        for invalid in ["", "abc", "0", "-1", "6.5"]:
            with self.assertRaisesRegex(ValueError, "positive|at least"):
                self.model.set_target(invalid)
        self.model.dataset = Dataset("DEMO-SGX", "Trending", ())
        with self.assertRaisesRegex(ValueError, "At least 4"):
            self.model.calculate()
        with self.assertRaisesRegex(ValueError, "before saving"):
            self.model.save_current()

    def test_empty_history_does_not_crash_with_previously_saved_lines(self):
        self.model.calculate()
        self.model.save_current()
        self.model.result = None
        self.model.dataset = Dataset("DEMO-SGX", "Oscillating", ())
        self.assertEqual(self.model.plot_lines(), [])
        self.assertEqual(len(self.model.saved_lines()), 1)
        with self.assertRaisesRegex(ValueError, "SQLite"):
            self.model.set_target(str(2**63))

    def test_active_policy_updates_display_and_preserves_older_saved_lines(self):
        self.model.select_dataset("DEMO-SGX", "Sideways")
        self.model.dataset = generate_mock_data("DEMO-SGX", "Sideways", sessions=252)
        self.model.store.save("DEMO-SGX", "Sideways", 192, 12)
        result = self.model.calculate()
        self.assertEqual((result.period, result.crossing_count, result.comparisons), (22, 33, 230))
        self.assertEqual(self.model.summary()["actual"], "36.16 / yr")
        self.assertEqual({line.period for line in self.model.plot_lines()}, {22, 192})
        restored = AnalyzerModel(LineStore(self.path))
        restored.select_dataset("DEMO-SGX", "Sideways")
        self.assertEqual(restored.saved_lines()[0].period, 192)

    def test_five_year_default_preserves_original_seeded_prefix(self):
        data = self.model.dataset
        self.assertEqual(len(data.prices), 1260)
        self.assertEqual(data.prices[:252], generate_mock_data(data.counter, data.scenario, 252).prices)
        result = self.model.calculate()
        self.assertEqual(result.history_sessions, 1260)
        self.assertGreaterEqual(result.comparisons, 504)
        self.assertLessEqual(result.period, 756)
