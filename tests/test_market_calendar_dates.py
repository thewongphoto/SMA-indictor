from datetime import datetime, timezone
from threading import Event
import math
import unittest

from sma_analyzer.backtest import equal_period_indices, period_sessions
from sma_analyzer.engine import optimize_sma
from sma_analyzer.schedule import SGT, expected_session_date, latest_due, next_due
from sma_analyzer.viewport import ChartViewport, available_timelines


class RealDateTests(unittest.TestCase):
    def test_us_targets_stay_at_6_sgt_on_both_sides_of_dst(self):
        for month in (1,7,11):
            now = datetime(2026,month,15,0,0,tzinfo=timezone.utc)
            due = latest_due("US",now)
            self.assertEqual((due.hour,due.minute),(6,0))
            self.assertIn(due.weekday(),{1,2,3,4,5})
            self.assertEqual(expected_session_date("US",due).weekday(),(due.weekday()-1)%7)

    def test_monday_us_target_and_sg_weekend_skip_to_correct_slots(self):
        now = datetime(2026,11,9,7,tzinfo=SGT)  # Monday
        self.assertEqual(latest_due("US",now).isoformat(),"2026-11-07T06:00:00+08:00")
        self.assertEqual(next_due("US",now).isoformat(),"2026-11-10T06:00:00+08:00")
        self.assertEqual(next_due("SG",now).isoformat(),"2026-11-09T17:30:00+08:00")

    def test_sg_exact_target_is_due_and_future_target_is_next_weekday(self):
        now = datetime(2026,11,6,17,30,tzinfo=SGT)
        self.assertEqual(latest_due("SG",now),now)
        self.assertEqual(next_due("SG",now).isoformat(),"2026-11-09T17:30:00+08:00")

    def test_calendar_backtest_window_uses_dates_not_252_sessions(self):
        dates=("2023-11-03","2024-11-04","2025-11-03","2025-11-04","2026-11-04")
        self.assertEqual(period_sessions("1Y","",len(dates),dates),2)
        self.assertEqual(period_sessions("Max","",len(dates),dates),5)

    def test_calendar_dca_uses_equal_calendar_intervals_and_next_eligible_close(self):
        dates=("2026-01-01","2026-01-02","2026-01-05","2026-01-12","2026-01-13","2026-01-20")
        self.assertEqual(equal_period_indices(0,5,2,list(range(6)),dates),(0,3))
        self.assertEqual(equal_period_indices(0,5,1,list(range(6)),dates),(0,))

    def test_chart_calendar_presets_cover_actual_dates_and_max_covers_every_bar(self):
        dates=("2020-01-02","2021-01-04","2022-01-04","2023-01-04","2024-01-04","2025-01-06","2026-01-05")
        self.assertEqual(available_timelines(len(dates),dates),("1Y","3Y","5Y","Max"))
        view=ChartViewport(len(dates))
        view.dates=dates
        view.show_timeline("1Y")
        self.assertEqual(view.bounds,(5,6))
        view.show_timeline("Max")
        self.assertEqual(view.bounds,(0,6))

    def test_long_history_vectorized_optimizer_matches_reference_with_gaps_and_ties(self):
        values=[100+3*math.sin(i/11)+i*.002 for i in range(1650)]
        values[500]=None
        values[700:708]=[100.0]*8
        periods=[2,5,10,20,50,100,200,300]
        fast=optimize_sma(values,6,periods)
        reference=optimize_sma(values,6,periods,use_fast=False)
        self.assertEqual(fast,reference)

    def test_optimization_can_be_cancelled_on_window_close(self):
        cancel=Event()
        cancel.set()
        with self.assertRaisesRegex(ValueError,"cancelled"):
            optimize_sma([100+math.sin(i) for i in range(1700)],6,cancel=cancel)
