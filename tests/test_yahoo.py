from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.yahoo_test_data import FakeYahooClient, NOW, bars_ending
from sma_analyzer.market_cache import MarketCache
from sma_analyzer.model import AnalyzerModel
from sma_analyzer.notifications import NotificationSettings, evaluate_dataset_eod
from sma_analyzer.securities import security_by_key
from sma_analyzer.storage import LineStore
from sma_analyzer.yahoo import (YahooMarketDataProvider, YFinanceClient, MarketDataError,
                                completed_bars, security_from_quote)


class YahooTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cache = MarketCache(self.root/"market_data.sqlite3")
        self.client = FakeYahooClient()
        self.now = NOW
        self.provider = YahooMarketDataProvider(self.cache, self.client, now=lambda: self.now)

    def apple(self):
        return self.provider.search("apple")[0]

    def test_submitted_search_persists_across_new_provider_and_normalizes_queries(self):
        first = self.provider.search("  APPLE  ")
        self.assertEqual(first[0].name, "Apple Inc.")
        self.assertEqual(len(self.client.calls), 1)
        offline = FakeYahooClient()
        offline.failure = RuntimeError("no internet")
        reopened = YahooMarketDataProvider(MarketCache(self.cache.path), offline, now=lambda: NOW)
        self.assertEqual(reopened.search("apple"), first)
        self.assertEqual(offline.calls, [])
        self.assertEqual(reopened.search("APPLE"), first)

    def test_explicit_search_refresh_and_empty_result_cache(self):
        self.provider.search("apple")
        self.provider.search("apple", force=True)
        self.assertEqual(len(self.client.calls), 2)
        self.assertEqual(self.provider.search("not-a-company"), ())
        calls = len(self.client.calls)
        self.assertEqual(self.provider.search("not-a-company"), ())
        self.assertEqual(len(self.client.calls), calls)

    def test_us_sg_stocks_and_etfs_only_and_packaged_logo(self):
        self.assertEqual(self.apple().logo, "apple")
        self.assertEqual(self.provider.search("dbs")[0].region, "SG")
        self.assertEqual(self.provider.search("spy")[0].region, "US")
        self.assertIsNone(security_from_quote(dict(symbol="BTC-USD", quoteType="CRYPTOCURRENCY", exchange="CCC")))
        self.assertIsNone(security_from_quote(dict(symbol="0700.HK", quoteType="EQUITY", exchange="HKG")))

    def test_first_load_downloads_full_history_and_dates_are_not_fabricated(self):
        security = self.apple()
        data = self.provider.historical_data(security)
        self.assertEqual(self.client.calls[-1], ("history", "AAPL", {"period":"max"}))
        self.assertEqual(len(data.prices), 1700)
        self.assertEqual(data.dates[0], self.client.bars[0]["date"])
        self.assertEqual(data.dates[-1], "2026-11-04")
        self.assertEqual(data.currency, "USD")
        self.assertFalse(data.is_simulated)
        self.assertEqual(data.scenario, "Yahoo EOD")

    def test_new_instance_uses_persisted_history_and_dynamic_identity_without_network(self):
        security = self.apple()
        data = self.provider.historical_data(security)
        client = FakeYahooClient()
        client.failure = RuntimeError("offline")
        reopened = YahooMarketDataProvider(MarketCache(self.cache.path), client, now=lambda: NOW)
        self.assertEqual(reopened.historical_data(security), data)
        self.assertEqual(client.calls, [])
        self.assertEqual(security_by_key(security.key).name, security.name)

    def test_multiple_saved_smas_share_history_and_saved_view_keeps_exact_period(self):
        security = self.apple()
        data = self.provider.historical_data(security)
        store = LineStore(self.root/"saved_lines.sqlite3")
        store.save(security.key, data.scenario, 20, 12)
        store.save(security.key, data.scenario, 50, 6)
        model = AnalyzerModel(store, self.provider)
        for line in store.list_all_lines():
            model.view_saved_line(line.id)
            self.assertEqual(model.result.period, line.period)
        self.assertEqual(sum(call[0] == "history" for call in self.client.calls), 1)
        self.assertEqual(model.dataset.scenario, "Yahoo EOD")

    def test_next_target_refresh_uses_overlap_and_merges_new_close(self):
        security = self.apple()
        self.provider.historical_data(security)
        self.now += timedelta(days=1)
        self.client.bars = bars_ending(date(2026,11,5),1701)
        data = self.provider.historical_data(security)
        self.assertEqual(self.client.calls[-1][2], {"start":"2026-10-25"})
        self.assertEqual(data.dates[-1], "2026-11-05")
        self.assertEqual(len(data.prices), 1701)
        self.assertEqual(len(data.dates), len(set(data.dates)))

    def test_failed_refresh_retains_data_and_reports_stale_not_empty(self):
        security = self.apple()
        before = self.provider.historical_data(security)
        self.now += timedelta(days=1)
        self.client.failure = RuntimeError("403 Forbidden: secret response must not be shown")
        stale = self.provider.historical_data(security)
        self.assertTrue(stale.stale)
        self.assertEqual(stale.prices, before.prices)
        self.assertIn("blocked", self.provider.last_warning)
        self.assertNotIn("secret", self.provider.last_warning)
        with self.assertRaises(MarketDataError):
            self.provider.historical_data(security, force=True, strict=True)
        self.assertEqual(self.cache.history(security.key)[0][-1]["date"], "2026-11-04")

    def test_empty_and_invalid_responses_cannot_erase_cached_history(self):
        security = self.apple()
        before = self.provider.historical_data(security)
        for bars in ([], [dict(date="2026-11-04",close=-1)]):
            self.client.bars = bars
            data = self.provider.historical_data(security, force=True)
            self.assertTrue(data.stale)
            self.assertEqual(data.prices, before.prices)

    def test_corporate_action_or_adjustment_change_resynchronizes_full_history(self):
        security = self.apple()
        self.provider.historical_data(security)
        self.client.bars[-2]["adj_close"] -= 1
        data = self.provider.historical_data(security, force=True)
        self.assertEqual(self.client.calls[-2][2], {"start":"2026-10-25"})
        self.assertEqual(self.client.calls[-1][2], {"period":"max"})
        self.assertFalse(data.stale)
        self.assertEqual(len(data.prices), 1700)

    def test_new_split_resynchronizes_even_when_adjusted_close_is_unavailable(self):
        self.client.bars = bars_ending(count=10)
        for bar in self.client.bars:
            bar["adj_close"] = None
        security = self.apple()
        self.provider.historical_data(security)
        extra = dict(self.client.bars[-1],date="2026-11-05",splits=2.0)
        self.client.bars.append(extra)
        self.now += timedelta(days=1)
        data = self.provider.historical_data(security)
        self.assertEqual(self.client.calls[-1][2],{"period":"max"})
        self.assertEqual(data.dates[-1],"2026-11-05")

    def test_truncated_full_refresh_does_not_discard_older_history(self):
        security = self.apple()
        before = self.provider.historical_data(security)
        self.client.bars = self.client.bars[-20:]
        after = self.provider.historical_data(security, full=True, force=True)
        self.assertTrue(after.stale)
        self.assertEqual(after.prices, before.prices)

    def test_full_refresh_missing_one_middle_date_keeps_complete_previous_revision(self):
        security = self.apple()
        before = self.provider.historical_data(security)
        del self.client.bars[500]
        data = self.provider.historical_data(security,force=True,full=True)
        self.assertTrue(data.stale)
        self.assertEqual(data.dates,before.dates)
        self.assertEqual(data.revision,before.revision)

    def test_null_updates_do_not_erase_known_prices_or_allow_missing_final_close(self):
        security = self.apple()
        before = self.provider.historical_data(security)
        self.client.bars[-3]["close"] = None
        self.client.bars[-1]["close"] = None
        updated = self.provider.historical_data(security, force=True)
        self.assertEqual(updated.prices, before.prices)
        self.assertEqual(updated.dates[-1], before.dates[-1])
        full = self.provider.historical_data(security, force=True, full=True)
        self.assertTrue(full.stale)
        self.assertEqual(full.prices, before.prices)

    def test_current_daily_bar_is_excluded_until_close_and_publication_buffer(self):
        security = self.apple()
        bars = bars_ending(date(2026,11,5),5)
        early = datetime(2026,11,5,17,tzinfo=timezone.utc)  # noon in New York
        self.assertEqual(completed_bars(bars,security,{},early)[-1]["date"],"2026-11-04")
        after = datetime(2026,11,5,22,tzinfo=timezone.utc)
        self.assertEqual(completed_bars(bars,security,{},after)[-1]["date"],"2026-11-05")

    def test_sg_current_daily_bar_is_excluded_before_1730_sgt(self):
        security = self.provider.search("dbs")[0]
        bars = bars_ending(date(2026,11,5),5)
        self.assertEqual(completed_bars(bars,security,{},datetime(2026,11,5,9,10,tzinfo=timezone.utc))[-1]["date"],"2026-11-04")
        self.assertEqual(completed_bars(bars,security,{},datetime(2026,11,5,9,30,tzinfo=timezone.utc))[-1]["date"],"2026-11-05")

    def test_health_once_per_launch_and_explicit_retry(self):
        self.assertTrue(self.provider.health_check()[0])
        self.assertTrue(self.provider.health_check()[0])
        self.assertEqual(self.client.calls, [("history","SPY",{"period":"5d"})])
        self.provider.health_check(force=True)
        self.assertEqual(len(self.client.calls), 2)

    def test_failed_health_is_not_automatically_retried(self):
        self.client.failure = RuntimeError("429 Too many requests")
        self.assertFalse(self.provider.health_check()[0])
        self.assertFalse(self.provider.health_check()[0])
        self.assertEqual(len(self.client.calls), 1)
        self.assertIn("limiting", self.provider.health_check()[1])

    def test_rate_limit_cooldown_survives_restart_and_does_not_block_cached_data(self):
        security = self.apple()
        data = self.provider.historical_data(security)
        self.client.failure = RuntimeError("429 Too many requests")
        self.assertFalse(self.provider.health_check()[0])
        before = len(self.client.calls)
        reopened = YahooMarketDataProvider(MarketCache(self.cache.path),self.client,now=lambda:NOW)
        self.assertFalse(reopened.health_check()[0])
        self.assertEqual(len(self.client.calls),before)
        self.assertEqual(reopened.historical_data(security).prices,data.prices)

    def test_health_does_not_mistake_old_successful_response_for_current_availability(self):
        self.client.bars = bars_ending(date(2025,11,4),10)
        success, warning = self.provider.health_check()
        self.assertFalse(success)
        self.assertIn("old observations", warning)
        self.assertEqual(self.cache.operations(1)[0][3],"failed")

    def test_live_alert_identity_uses_actual_session_date_not_mutable_index(self):
        security = self.apple()
        data = self.provider.historical_data(security)
        data = replace(data,prices=(100,99,98,97),dates=("2026-10-30","2026-11-02","2026-11-03","2026-11-04"))
        store = LineStore(self.root/"saved_lines.sqlite3")
        store.save(security.key,data.scenario,2,12)
        line = store.list_all_lines()[0]
        store.set_notifications(line.id,"phone",True)
        line = store.get_line(line.id)
        settings = NotificationSettings(phone_monitor=True)
        first = evaluate_dataset_eod(data,line,settings)[0]
        extended = replace(data,prices=(101,)+data.prices,dates=("2026-10-29",)+data.dates)
        second = evaluate_dataset_eod(extended,line,settings)[0]
        self.assertEqual(first.key,second.key)
        self.assertIn("2026-11-04",first.body)
        self.assertNotIn("SIMULATED DATA",first.body)

    def test_explicit_clear_keeps_saved_parameters_identities_and_preferences(self):
        security = self.apple()
        data = self.provider.historical_data(security)
        store = LineStore(self.root/"saved_lines.sqlite3")
        store.save(security.key, data.scenario, 20, 12)
        self.cache.set_preference("example", True)
        self.cache.clear_downloads()
        self.assertEqual(self.cache.history(security.key)[0], [])
        self.assertIsNone(self.cache.search("apple"))
        self.assertEqual(store.list_all_lines()[0].period, 20)
        self.assertEqual(self.cache.security(security.key), security)
        self.assertTrue(self.cache.preference("example"))

    def test_existing_demo_library_stays_synthetic_with_yahoo_provider(self):
        store = LineStore(self.root/"saved_lines.sqlite3")
        store.save("DEMO-SGX","Oscillating",20,12)
        model = AnalyzerModel(store,self.provider)
        model.view_saved_line(store.list_all_lines()[0].id)
        self.assertIn("SIMULATED", model.dataset.label)
        self.assertEqual(self.client.calls, [])

    def test_cache_network_lease_is_atomic_and_recoverable_after_expiry(self):
        self.assertTrue(self.cache.lease("network","a",100,10))
        self.assertFalse(MarketCache(self.cache.path).lease("network","b",105,10))
        self.assertTrue(self.cache.lease("network","b",111,10))
        self.cache.release_lease("network","a")
        self.assertFalse(self.cache.lease("network","c",112,10))

    @unittest.skipUnless(importlib.util.find_spec("yfinance"), "desktop-only dependency")
    def test_real_transport_adapter_uses_explicit_options_and_reuses_metadata(self):
        import pandas as pd
        frame = pd.DataFrame({"Close":[100.,101.], "Adj Close":[99.,100.], "Volume":[20,21]},
                             index=pd.to_datetime(["2026-11-03","2026-11-04"]))
        with patch("yfinance.Ticker") as ticker:
            ticker.return_value.history.return_value = frame
            ticker.return_value.get_history_metadata.return_value = {"currency":"USD",
                "exchangeTimezoneName":"America/New_York"}
            client = YFinanceClient(self.root/"yf")
            bars, metadata = client.history("AAPL",period="max")
            options = ticker.return_value.history.call_args.kwargs
            self.assertEqual(options["interval"],"1d")
            self.assertFalse(options["auto_adjust"])
            self.assertFalse(options["repair"])
            self.assertEqual(bars[-1]["date"],"2026-11-04")
            self.assertEqual(metadata["currency"],"USD")
            ticker.return_value.get_history_metadata.assert_called_once()
