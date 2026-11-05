"""Dividend/split-adjusted analysis, cache upgrades and return calculations."""
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.yahoo_test_data import FakeYahooClient,NOW,bars_ending
from scripts.yahoo_json_test_data import chart_payload,Response,Session
from sma_analyzer.backtest import compare_investments
from sma_analyzer.engine import simple_moving_average,crossover_events
from sma_analyzer.market_cache import MarketCache
from sma_analyzer.mobile_yahoo import YahooJSONClient
from sma_analyzer.model import AnalyzerModel
from sma_analyzer.storage import LineStore
from sma_analyzer.yahoo import YahooMarketDataProvider,MarketDataError,PRICE_BASIS,SCENARIO


def dividend_bars():
    bars=bars_ending(count=8)
    for bar,close,adjusted in zip(bars,(100,100,90,90,95,100,98,100),(90,90,90,90,95,100,98,100)):
        bar.update(close=float(close),open=float(close),high=close+1.,low=close-1.,adj_close=float(adjusted))
    bars[2]["dividends"]=10.
    return bars


class DividendAdjustmentTests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.cache=MarketCache(self.root/"market.sqlite3")
        self.client=FakeYahooClient(dividend_bars())
        self.provider=YahooMarketDataProvider(self.cache,self.client,now=lambda:NOW)
        self.security=self.provider.search("apple")[0]

    def test_all_analysis_uses_adj_close_while_cache_retains_both_series(self):
        data=self.provider.historical_data(self.security)
        self.assertEqual(data.price_basis,PRICE_BASIS)
        self.assertEqual(data.prices,tuple(bar["adj_close"] for bar in self.client.bars))
        self.assertNotEqual(data.prices,tuple(bar["close"] for bar in self.client.bars))
        raw=self.cache.history(self.security.key)[0]
        self.assertEqual((raw[0]["close"],raw[0]["adj_close"]),(100.,90.))
        model=AnalyzerModel(LineStore(self.root/"lines.sqlite3"),self.provider)
        model.apply_dataset(data)
        result=model.result_for_dataset(data,2,12)
        model.apply_result(result)
        average=tuple(simple_moving_average(data.prices,2))
        self.assertEqual(model.plot_lines()[0].sma,average)
        self.assertEqual(result.events,crossover_events(data.prices,average))
        report=compare_investments(data.prices,result.sma,result.events,len(data.prices),data.dates)
        self.assertEqual(len(report.dca.indices),1)
        # USD 100 held across the dividend: 100 * AdjEnd / AdjEntry.
        # No second addition of the USD 10 distribution to that ending value.
        self.assertAlmostEqual(report.dca.ending_value,100*100/90)
        self.assertAlmostEqual(report.dca.return_percent,(100/90-1)*100)
        self.assertAlmostEqual(report.crossings.ending_value,100*data.prices[-1]/result.events[0].price)

    def test_complete_legacy_cache_reuses_adjustments_offline_without_http(self):
        self.cache.merge_history(self.security,dividend_bars(),NOW.timestamp())
        offline=FakeYahooClient()
        offline.failure=RuntimeError("offline")
        provider=YahooMarketDataProvider(MarketCache(self.cache.path),offline,now=lambda:NOW)
        data=provider.historical_data(self.security)
        self.assertEqual(data.prices[0],90.)
        self.assertEqual(provider.cached_data(self.security).prices,data.prices)
        self.assertEqual(offline.calls,[])

    def test_legacy_cache_without_adjustments_requires_max_and_preserves_saved_period_and_color(self):
        legacy=dividend_bars()
        for bar in legacy:
            del bar["adj_close"]
        self.cache.merge_history(self.security,legacy,NOW.timestamp())
        store=LineStore(self.root/"lines.sqlite3")
        store.save(self.security.key,SCENARIO,2,12)
        model=AnalyzerModel(store,self.provider)
        with self.assertRaisesRegex(MarketDataError,"Dividend-adjusted"):
            self.provider.cached_data(self.security)
        model.view_saved_line(store.list_all_lines()[0].id)
        self.assertEqual(self.client.calls[-1],("history","AAPL",{"period":"max"}))
        self.assertEqual(model.result.period,2)
        self.assertEqual(model.plot_lines()[0].color_index,0)
        self.assertEqual(model.dataset.prices[0],90.)

    def test_missing_adjustments_and_offline_legacy_cache_never_fall_back_to_raw(self):
        legacy=dividend_bars()
        for bar in legacy:
            bar["adj_close"]=None
        self.cache.merge_history(self.security,legacy,NOW.timestamp())
        self.client.failure=RuntimeError("503")
        with self.assertRaises(MarketDataError):
            self.provider.historical_data(self.security)
        self.assertEqual(self.cache.history(self.security.key)[0],legacy)
        self.client.failure=None
        self.client.bars=legacy
        with self.assertRaisesRegex(MarketDataError,"Dividend-adjusted"):
            self.provider.historical_data(self.security)
        self.assertEqual(self.cache.history(self.security.key)[0],legacy)

    def test_invalid_adjustments_keep_prior_adjusted_revision_atomically(self):
        before=self.provider.historical_data(self.security)
        for invalid in (None,0,-1,True,float("nan")):
            with self.subTest(invalid=invalid):
                self.client.bars=dividend_bars()
                self.client.bars[1]["adj_close"]=invalid
                after=self.provider.historical_data(self.security,force=True,full=True)
                self.assertTrue(after.stale)
                self.assertEqual(after.prices,before.prices)
                self.assertEqual(after.revision,before.revision)
                self.assertEqual(self.cache.history(self.security.key)[0][1]["adj_close"],90.)

    def test_first_download_missing_adjustment_does_not_create_partial_cache(self):
        self.client.bars[2]["adj_close"]=None
        with self.assertRaisesRegex(MarketDataError,"Dividend-adjusted"):
            self.provider.historical_data(self.security)
        self.assertEqual(self.cache.history(self.security.key),([],None,0))

    def test_real_gaps_are_retained_without_turning_adjustment_into_an_observation(self):
        self.client.bars[2]["close"]=None
        data=self.provider.historical_data(self.security)
        self.assertIsNone(data.prices[2])
        self.assertEqual(data.prices[3],90.)

    def test_new_dividend_refreshes_older_adjustments_outside_incremental_window(self):
        self.client.bars=bars_ending()
        before=self.provider.historical_data(self.security)
        for bar in self.client.bars:
            bar["adj_close"] *= .95
        self.client.bars.append(dict(self.client.bars[-1],date="2026-11-05",dividends=2.,adj_close=103.,close=103.))
        self.provider.now=lambda:NOW+timedelta(days=1)
        after=self.provider.historical_data(self.security)
        self.assertEqual([call[2] for call in self.client.calls[-2:]],
                         [{"start":"2026-10-25"},{"period":"max"}])
        self.assertEqual(after.prices[0],before.prices[0]*.95)
        self.assertEqual(after.prices[-1],103.)
        self.assertEqual(len(after.prices),1701)

    def test_full_resync_never_splices_a_missing_observation_from_an_old_dividend_basis(self):
        before=self.provider.historical_data(self.security)
        for bar in self.client.bars:
            bar["adj_close"] *= .95
        self.client.bars[3]["close"]=None
        self.client.bars[3]["adj_close"]=None
        after=self.provider.historical_data(self.security,force=True)
        self.assertEqual(self.client.calls[-1][2],{"period":"max"})
        self.assertTrue(after.stale)
        self.assertEqual(after.prices,before.prices)
        self.assertEqual(after.revision,before.revision)

    def test_old_raw_analysis_choice_invalidated_even_when_adjusted_equals_close(self):
        self.client.bars=bars_ending(count=10)
        data=self.provider.historical_data(self.security)
        store=LineStore(self.root/"lines.sqlite3")
        # The old analysis key omitted the price basis.
        raw_hash=hashlib.sha256(json.dumps((1,data.version,data.dates,list(data.prices)),
            separators=(",",":"),allow_nan=False).encode()).hexdigest()
        store.cache_choice(data.counter,data.scenario,12,raw_hash,2)
        model=AnalyzerModel(store,self.provider)
        model.apply_dataset(data)
        self.assertFalse(model.reuse_result())
        result=model.calculate()
        model.apply_dataset(replace(data))
        self.assertTrue(model.reuse_result())
        self.assertEqual(model.result,result)

    def test_mobile_http_and_desktop_contract_use_identical_provider_adjustments(self):
        bars=dividend_bars()
        session=Session(Response(payload=chart_payload(bars)))
        client=YahooJSONClient(self.root/"state",session=session,observer=self.cache.operation,now=lambda:NOW)
        provider=YahooMarketDataProvider(self.cache,client,now=lambda:NOW)
        mobile=provider.historical_data(self.security)
        self.assertEqual(mobile.prices,tuple(bar["adj_close"] for bar in bars))
        self.assertEqual(session.calls[0][1]["params"]["includeAdjustedClose"],"true")
        self.assertEqual(len(session.calls),1)
