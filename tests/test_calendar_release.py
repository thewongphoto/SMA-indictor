"""Release checks for the fixed-day annual target and both scoring routes."""
from datetime import date,timedelta
from fractions import Fraction
import importlib.util
import random
from unittest import TestCase,skipUnless

from sma_analyzer.engine import optimize_sma,_fast_optimization
from sma_analyzer.policy import calendar_weights,maximum_sma_period


class CalendarReleaseTests(TestCase):
    def test_per_year_target_is_an_average_not_a_calendar_year_quota(self):
        prices=(12.,10.,12.,10.,12.,13.)
        dates=('2023-12-29','2024-01-01','2024-02-01',
               '2024-03-01','2024-04-01','2025-12-31')
        result=optimize_sma(prices,1,[2],dates=dates)
        self.assertEqual(result.calendar_days,730)
        self.assertEqual(result.crossing_count,2)
        self.assertEqual(result.frequency,Fraction(1))
        self.assertEqual(result.frequency_error,0)
        self.assertEqual([dates[event.index][:4] for event in result.events],['2024','2024'])

    @skipUnless(importlib.util.find_spec('numpy'),'NumPy is optional on the mobile build')
    def test_real_numpy_route_matches_mobile_without_silently_falling_back(self):
        rng=random.Random(4131)
        prices=[100.+rng.random()*30 for _ in range(1640)]
        for index in (300,550,900):
            prices[index]=None
        day=date(2015,1,1)
        dates=[]
        for _ in prices:
            day+=timedelta(days=rng.choice((1,1,1,2,3,4)))
            dates.append(day.isoformat())
        periods=(2,3,5,10,20,50,100,200)
        expected=optimize_sma(prices,12,periods,dates=dates,use_fast=False)
        actual=_fast_optimization(prices,periods,
            len(prices)-maximum_sma_period(len(prices)),12,None,
            calendar_weights(dates,len(prices)))
        self.assertIsNotNone(actual)
        self.assertEqual(actual,expected)
