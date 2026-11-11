from unittest import TestCase

from sma_analyzer.logo_motion import CROSSING_SECONDS, DRAW_SECONDS, LOGO_PERIOD, logo_frame
from scripts.spinner_metrics import observe_logo


class LogoMotionTests(TestCase):
    def test_plus_waits_for_the_lines_to_reach_the_crossing(self):
        self.assertEqual(logo_frame(CROSSING_SECONDS-.01).plus_opacity, 0)
        self.assertGreater(logo_frame(CROSSING_SECONDS+.06).plus_opacity, 0)
        self.assertEqual(logo_frame(CROSSING_SECONDS+.13).plus_opacity, 1)
        self.assertLess(logo_frame(CROSSING_SECONDS+.06).progress, 1)
        self.assertEqual(logo_frame(DRAW_SECONDS).progress, 1)

    def test_continuous_clock_repeats_the_same_paths_past_one_cycle(self):
        expected = logo_frame(.35)
        for cycle in range(1, 11):
            frame = logo_frame(cycle*LOGO_PERIOD+.35)
            self.assertAlmostEqual(frame.progress, expected.progress)
            self.assertEqual(frame.plus_opacity, expected.plus_opacity)
        self.assertEqual(logo_frame(1.31).opacity, 0)
        self.assertEqual(logo_frame(LOGO_PERIOD+.1).opacity, 1)

    def test_frame_rate_does_not_change_the_elapsed_drawing_speed(self):
        for fps in (12, 60, 120):
            samples = [(index/fps, index/fps) for index in range(1, int(3.3*fps)+1)]
            _, problems = observe_logo(samples, 0, 3.3, period=LOGO_PERIOD)
            self.assertEqual(problems, [])

    def test_stopped_or_paused_drawings_cannot_pass_sustained_motion_check(self):
        stopped = [(index/60, min(index/60, LOGO_PERIOD)) for index in range(1, 199)]
        self.assertTrue(observe_logo(stopped, 0, 3.3)[1])
        paused = [(index/60, index/60) for index in range(1, 199) if not 1.1<index/60<1.6]
        self.assertTrue(any("stalled" in item for item in observe_logo(paused, 0, 3.3)[1]))
