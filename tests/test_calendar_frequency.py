from datetime import date,timedelta
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from sma_analyzer.backtest import period_sessions
from sma_analyzer.engine import optimize_sma,simple_moving_average
from sma_analyzer.model import AnalyzerModel
from sma_analyzer.policy import calendar_weights,observable_calendar_days
from sma_analyzer.storage import LineStore
from sma_analyzer.viewport import ChartViewport
from sma_analyzer.yahoo import HistoricalDataset


class CalendarFrequencyTests(TestCase):
    prices=(12.,10.,12.,10.,12.)
    dates=('2026-01-08','2026-01-09','2026-01-12','2026-01-13','2026-01-14')

    def test_weekend_and_holiday_time_count_in_a_365_day_year(self):
        result=optimize_sma(self.prices,6,dates=self.dates)
        self.assertEqual(result.crossing_count,2)
        self.assertEqual(result.comparisons,3)
        self.assertEqual(result.calendar_days,5)  # Friday to Wednesday, including weekend.
        self.assertEqual(result.frequency,Fraction(2*365,5))
        self.assertEqual(result.usable_years,5/365)
        self.assertEqual(result.target_crossings,6*(5/365))
        # An extra non-trading day adds elapsed time without adding a close.
        extended=self.dates[:-1]+('2026-01-15',)
        self.assertEqual(optimize_sma(self.prices,6,dates=extended).frequency,Fraction(2*365,6))

    def test_leap_year_also_normalizes_to_exactly_365_days(self):
        dates=('2023-02-27','2023-02-28','2023-06-01','2023-12-01','2024-02-29')
        result=optimize_sma(self.prices,6,dates=dates)
        self.assertEqual(result.calendar_days,366)
        self.assertEqual(result.frequency,Fraction(2*365,366))
        self.assertEqual(period_sessions('1Y','',len(dates),dates),3)
        view=ChartViewport(len(dates));view.dates=dates
        view.show_timeline('1Y')
        self.assertEqual(view.bounds,(2,4))

    def test_missing_observations_and_rewarmup_do_not_invent_observable_time(self):
        prices=(12.,10.,12.,None,10.,12.,10.,12.)
        dates=('2026-01-02','2026-01-05','2026-01-06','2026-01-07',
               '2026-01-08','2026-01-09','2026-01-12','2026-01-13')
        weights=calendar_weights(dates,len(prices))
        self.assertEqual(observable_calendar_days(prices,simple_moving_average(prices,2),weights),5)

    def test_live_dates_must_be_complete_strictly_increasing_and_valid(self):
        for dates in (self.dates[:-1],tuple(reversed(self.dates)),self.dates[:-1]+(self.dates[-2],),
                      self.dates[:-1]+('2026-02-30',)):
            with self.assertRaises(ValueError):
                optimize_sma(self.prices,6,dates=dates)

    def test_optimized_period_matches_an_independent_calendar_objective(self):
        prices=tuple(100+7*math.sin(i/3)+math.sin(i/7) for i in range(80))
        dates=tuple((date(2025,1,1)+timedelta(days=i*3)).isoformat() for i in range(80))
        periods=(2,5,10,15,20)
        results=[AnalyzerModel.result_for_dataset(HistoricalDataset('YAHOO:T',prices,dates,'USD','America/New_York',1,1),p,6) for p in periods]
        expected=min(results,key=lambda r:(abs(Fraction(r.crossing_count*365,(date.fromisoformat(dates[-1])-date.fromisoformat(dates[r.period-1])).days)-6),r.period))
        self.assertEqual(optimize_sma(prices,6,periods,dates=dates),expected)

    def test_fast_and_mobile_paths_match_on_long_calendar_histories_with_gaps(self):
        prices=[100+3*math.sin(i/11)+i*.002 for i in range(1700)]
        prices[500]=None
        prices[700:708]=[100.]*8
        dates=tuple((date(2017,1,2)+timedelta(days=(i//5)*7+i%5)).isoformat() for i in range(len(prices)))
        periods=(2,5,10,20,50,100,200,300)
        fast=optimize_sma(prices,6,periods,dates=dates)
        self.assertEqual(fast,optimize_sma(prices,6,periods,dates=dates,use_fast=False))
        self.assertIsNotNone(fast.calendar_days)

    def test_old_live_optimizer_cache_expires_but_saved_periods_and_flags_survive(self):
        data=HistoricalDataset('YAHOO:AAPL',self.prices,self.dates,'USD','America/New_York',1,1)
        with TemporaryDirectory() as directory:
            store=LineStore(Path(directory)/'lines.sqlite3')
            model=AnalyzerModel(store);model.apply_dataset(data)
            old_payload=json.dumps((2,data.version,data.price_basis,data.dates,list(self.prices)),separators=(',',':'),allow_nan=False).encode()
            store.cache_choice(data.counter,data.scenario,12,hashlib.sha256(old_payload).hexdigest(),2)
            self.assertFalse(model.reuse_result())
            store.save(data.counter,data.scenario,2,12)
            line,=store.list_all_lines();store.set_notifications(line.id,'phone',False)
            self.assertTrue(model.reuse_result())
            self.assertEqual(model.result.period,2)
            self.assertEqual(model.result.frequency,Fraction(2*365,5))
            self.assertFalse(store.get_line(line.id).push_enabled)
