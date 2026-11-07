from threading import Event
from unittest import TestCase
from unittest.mock import patch

from sma_analyzer.engine import optimize_sma


class OptimizationResponsivenessTests(TestCase):
    def test_cooperative_scoring_preserves_exact_reference_result(self):
        prices=[12.,10.,10.,14.,11.,13.,10.]*120
        prices[50]=prices[300]=None
        expected=optimize_sma(prices,6,use_fast=False)
        with patch("sma_analyzer.engine.time.sleep") as sleep:
            observed=optimize_sma(prices,6,cancel=Event(),use_fast=False)
        self.assertEqual(observed,expected)
        self.assertTrue(all(call.args==(0,) for call in sleep.call_args_list))

    def test_cancellation_is_checked_within_a_long_candidate(self):
        cancel=Event()
        with patch("sma_analyzer.engine.time.perf_counter",side_effect=range(1000)), \
             patch("sma_analyzer.engine.time.sleep",side_effect=lambda _:cancel.set()):
            with self.assertRaisesRegex(ValueError,"cancelled"):
                optimize_sma([10.,12.]*5000,12,candidates=[20],cancel=cancel,use_fast=False)
