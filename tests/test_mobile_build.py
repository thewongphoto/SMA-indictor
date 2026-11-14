import configparser
from fractions import Fraction
import math
from pathlib import Path
import random
import unittest

from sma_analyzer.engine import (optimize_sma,simple_moving_average,crossover_events,_rolling_score)
from sma_analyzer.policy import observable_comparisons
from sma_analyzer.version import APP_VERSION


class MobileBuildTests(unittest.TestCase):
    def test_apk_includes_portable_http_timezone_dependencies_and_matching_version(self):
        config=configparser.ConfigParser()
        config.read(Path(__file__).parents[1]/"buildozer.spec")
        requirements=[value.split("==")[0] for value in config["app"]["requirements"].split(",")]
        self.assertIn("requests",requirements)
        self.assertIn("tzdata",requirements)
        for dependency in ("urllib3","idna","charset_normalizer","certifi"):
            self.assertIn(dependency,requirements)
        self.assertNotIn("yfinance",requirements)
        self.assertNotIn("pandas",requirements)
        self.assertNotIn("curl_cffi",requirements)
        self.assertEqual(config["app"]["version"],APP_VERSION)
        self.assertEqual(config["app"]["package.name"],"smaanalyzer")
        self.assertEqual(config["app"]["package.domain"],"org.thewongphoto")
        self.assertIn("androidx.work:work-runtime:",config["app"]["android.gradle_dependencies"])
        self.assertNotIn("play-services-auth",config["app"]["android.gradle_dependencies"])

    def test_shared_chart_asset_has_a_narrow_native_packaging_allowlist(self):
        import fnmatch
        config=configparser.ConfigParser();config.read(Path(__file__).parents[1]/'buildozer.spec')
        def included(name):
            excluded=any(fnmatch.fnmatch(name,p) for p in config['app']['source.exclude_patterns'].split(','))
            if any(fnmatch.fnmatch(name,p) for p in config['app']['source.include_patterns'].split(',')):excluded=False
            return not excluded and name.rsplit('.',1)[-1] in config['app']['source.include_exts'].split(',')
        self.assertTrue(included('sma_analyzer/assets/chart-style.json'))
        self.assertTrue(included('sma_analyzer/assets/fonts/OFL.txt'))
        self.assertFalse(included('token.json'))
        self.assertFalse(included('sma_analyzer/user-emails.json'))

    def test_one_pass_mobile_scores_match_reference_arithmetic_gaps_and_equality(self):
        rng=random.Random(7)
        prices=[100+rng.randint(-5,5)*.1 for _ in range(300)]
        prices[60:65]=[None]*5
        prices[120:130]=[100.]*10
        for period in (2,3,5,20,50,100):
            average=simple_moving_average(prices,period)
            self.assertEqual(_rolling_score(prices,period),
                             (len(crossover_events(prices,average)),observable_comparisons(prices,average)))

    def test_mobile_winner_matches_full_reference_candidate_selection(self):
        prices=[100+math.sin(i/7)+i*.01 for i in range(600)]
        prices[300]=None
        candidates=(2,3,5,10,20,50,80,96)
        target=12
        def score(period):
            average=simple_moving_average(prices,period)
            comparisons=observable_comparisons(prices,average)
            events=crossover_events(prices,average)
            return abs(Fraction(len(events)*252,comparisons)-target),period
        expected=min(candidates,key=score)
        self.assertEqual(optimize_sma(prices,target,candidates,use_fast=False).period,expected)

    def test_overflowing_rolling_average_is_excluded_like_the_reference(self):
        prices=[1e308]*10
        average=simple_moving_average(prices,2)
        self.assertEqual(_rolling_score(prices,2),
                         (len(crossover_events(prices,average)),observable_comparisons(prices,average)))
