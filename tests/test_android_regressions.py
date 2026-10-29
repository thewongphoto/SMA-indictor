"""Device-independent checks for the failures reported during phone testing."""
import base64
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.prepare_android_signing import prepare_identity
from sma_analyzer.android_window import WindowMetrics
from sma_analyzer.engine import crossover_events, simple_moving_average
from sma_analyzer.model import AnalyzerModel
from sma_analyzer.policy import observable_comparisons
from sma_analyzer.storage import LineStore


class AndroidRegressionTests(unittest.TestCase):
    def test_safe_bars_and_keyboard_are_not_added_twice(self):
        bars = WindowMetrics(top=24, bottom=24, width=440, height=920)
        self.assertEqual(bars.content_bounds(440, 920), (0, 24, 440, 872))
        ime = WindowMetrics(top=24, bottom=24, keyboard=300, width=440, height=920)
        self.assertEqual(ime.content_bounds(440, 920), (0, 300, 440, 596))
        self.assertEqual(bars.content_bounds(440, 920), (0, 24, 440, 872))

    def test_native_pixels_scale_to_kivy_and_already_inset_surface_stays_full(self):
        metrics = WindowMetrics(left=30, top=72, right=30, bottom=48, width=1320, height=2760)
        self.assertEqual(metrics.content_bounds(440, 920), (10, 16, 420, 880))
        self.assertEqual(WindowMetrics(width=440, height=872).content_bounds(440, 872), (0, 0, 440, 872))

    def test_saved_lines_survive_process_exit_across_all_counters_and_scenarios(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/"saved_lines.sqlite3"
            # os._exit skips graceful app/SQLite cleanup. Each completed store
            # operation must already be committed before a force-stop.
            code = """
import os, sys
from sma_analyzer.storage import LineStore
from sma_analyzer.notifications import NotificationSettings
store = LineStore(sys.argv[1])
store.save('DEMO-SGX', 'Trending', 11, 12)
store.save('DEMO-US', 'Sideways', 254, 9)
store.save_notification_settings(NotificationSettings(email='reader@example.com',phone_buy=True))
line = store.list_lines('DEMO-US','Sideways')[0]
store.set_visible(line.id,False)
store.set_notifications(line.id,'phone',True)
store.set_notifications(line.id,'email',True)
store.record_delivery('persisted-test')
os._exit(0)
"""
            subprocess.run([sys.executable, "-c", code, str(path)], check=True)
            store = LineStore(path)
            self.assertEqual(len(store.list_all_lines()), 2)
            self.assertEqual(len(store.list_lines("DEMO-SGX", "Oscillating")), 0)
            line = store.list_lines("DEMO-US", "Sideways")[0]
            self.assertFalse(line.visible)
            self.assertTrue(line.push_enabled and line.email_enabled)
            self.assertEqual(store.notification_settings().email, "reader@example.com")
            self.assertTrue(store.notification_settings().phone_buy)
            self.assertTrue(store.was_delivered("persisted-test"))

    def test_view_saved_line_preserves_exact_period_target_and_full_history_statistics(self):
        with TemporaryDirectory() as directory:
            store = LineStore(Path(directory)/"data.sqlite3")
            # Older saved periods beyond the current optimizer cap are viewable.
            store.save("DEMO-US", "Trending", 1000, 9)
            saved = store.list_all_lines()[0]
            store.set_visible(saved.id, False)
            model = AnalyzerModel(store)
            with patch("sma_analyzer.model.optimize_sma", side_effect=AssertionError("Do not re-optimize saved parameters")):
                model.view_saved_line(saved.id)
            result = model.result
            self.assertEqual((model.dataset.counter, model.dataset.scenario), ("DEMO-US", "Trending"))
            self.assertEqual((result.period, model.target_frequency), (1000, 9))
            self.assertEqual(result.sma, tuple(simple_moving_average(model.dataset.prices, 1000)))
            self.assertEqual(result.events, crossover_events(model.dataset.prices, result.sma))
            self.assertEqual(result.comparisons, observable_comparisons(model.dataset.prices, result.sma))
            self.assertTrue(model.viewing_saved and model.plot_lines()[0].active)
            self.assertFalse(store.get_line(saved.id).visible)
            with self.assertRaisesRegex(ValueError, "no longer saved"):
                model.view_saved_line(saved.id+1)
            self.assertIs(model.result, result)


class SigningIdentityTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/"debug.keystore"
        # These tests check restore/fail-closed policy, not cryptography. A real
        # keytool round-trip is also recorded in the Android validation report.
        self.signature = patch("scripts.prepare_android_signing.fingerprint",
            side_effect=lambda path: "AA:AA" if Path(path).read_bytes()==b"original" else "BB:BB")
        self.signature.start()
        self.addCleanup(self.signature.stop)

    def test_missing_cache_and_secret_never_generate_a_different_key(self):
        with self.assertRaisesRegex(ValueError, "refusing to generate"):
            prepare_identity(self.path)
        self.assertFalse(self.path.exists())

    def test_secret_restores_original_identity_after_cache_loss(self):
        encoded = base64.b64encode(b"original").decode()
        self.assertEqual(prepare_identity(self.path, encoded, "AA:AA"), "AA:AA")
        self.assertEqual(self.path.read_bytes(), b"original")
        self.assertEqual(prepare_identity(self.path), "AA:AA")

    def test_wrong_secret_or_fingerprint_cannot_replace_original(self):
        self.path.write_bytes(b"original")
        encoded = base64.b64encode(b"different").decode()
        with self.assertRaisesRegex(ValueError, "differs from the cached key"):
            prepare_identity(self.path, encoded)
        with self.assertRaisesRegex(ValueError, "differs from ANDROID_SIGNING_SHA1"):
            prepare_identity(self.path, expected_sha1="BB:BB")
        self.assertEqual(self.path.read_bytes(), b"original")

    def test_invalid_secret_has_helpful_error_and_keeps_cached_key(self):
        self.path.write_bytes(b"original")
        with self.assertRaisesRegex(ValueError, "not valid base64"):
            prepare_identity(self.path, "not-base64!")
        self.assertEqual(self.path.read_bytes(), b"original")
