from unittest import TestCase

from scripts.spinner_metrics import observe_spinner


class SpinnerMetricsTests(TestCase):
    def trace(self,times,rate=400):
        return [(stamp,(stamp-times[0])*rate%360) for stamp in times]

    def test_reported_55_frame_ci_run_keeps_rotating_at_the_correct_speed(self):
        # The failed job measured 1271.91 degrees, a 71.64ms worst gap and
        # only 55 frames. It was rejected solely by a fixed >60-frame limit.
        span=1271.9111076/400
        step=(span-.071640211)/53
        times=[.08]
        for index in range(54):
            times.append(times[-1]+(.071640211 if index==25 else step))
        report,problems=observe_spinner(self.trace(times),0,3.336909854)
        self.assertEqual(problems,[])
        self.assertEqual(report["frames"],55)
        self.assertAlmostEqual(report["rotation_degrees"],1271.9111076)

    def test_high_frame_rate_also_passes_without_changing_the_required_motion(self):
        _,problems=observe_spinner(self.trace([index/70 for index in range(232)]),0,3.31)
        self.assertEqual(problems,[])

    def test_old_one_revolution_then_stop_bug_still_fails(self):
        _,problems=observe_spinner(self.trace([index/60 for index in range(55)]),0,3.3)
        self.assertTrue(any("three revolutions" in item for item in problems))
        self.assertTrue(any("stalled" in item for item in problems))

    def test_a_mid_run_pause_cannot_pass_by_making_up_rotation_later(self):
        times=[index/60 for index in range(199) if not 1.1<index/60<1.6]
        _,problems=observe_spinner(self.trace(times),0,3.3)
        self.assertTrue(any("stalled" in item for item in problems))

    def test_wrong_clock_speed_and_no_updates_both_fail(self):
        times=[index/60 for index in range(199)]
        _,problems=observe_spinner(self.trace(times,rate=800),0,3.3)
        self.assertTrue(any("elapsed time" in item for item in problems))
        _,problems=observe_spinner([],0,3.3)
        self.assertGreaterEqual(len(problems),2)
