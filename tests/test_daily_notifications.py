from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock,patch
from concurrent.futures import ThreadPoolExecutor

from scripts.yahoo_test_data import FakeYahooClient,NOW
from sma_analyzer.daily_notifications import run_daily_notifications,enabled_lines
from sma_analyzer.market_cache import MarketCache
from sma_analyzer.native_schedule import configuration
from sma_analyzer.notifications import NotificationSettings,evaluate_dataset_eod
from sma_analyzer.schedule import SGT
from sma_analyzer.storage import LineStore
from sma_analyzer.yahoo import YahooMarketDataProvider


class DailyNotificationsTests(TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.store=LineStore(self.root/"saved_lines.sqlite3")
        self.client=FakeYahooClient()
        self.provider=YahooMarketDataProvider(MarketCache(self.root/"market.sqlite3"),self.client,now=lambda:NOW)
        self.us=self.provider.search("apple")[0]
        self.sg=self.provider.search("dbs")[0]
        self.store.save_notification_settings(NotificationSettings(phone_buy=True,phone_monitor=True))
        self.store.save(self.us.key,self.provider.scenario,2,12)
        self.line=self.store.list_all_lines()[0]
        self.store.set_notifications(self.line.id,"phone",True)
        self.phone=Mock()

    def run_job(self,region="US",now=NOW):
        return run_daily_notifications(self.store,self.provider,region,self.phone,now)

    def test_configuration_uses_enabled_regions_and_shared_singapore_times(self):
        config=configuration(self.store,self.provider,self.root)
        self.assertEqual(config["regions"],["US"])
        self.assertEqual((config["schedules"]["US"]["hour"],config["schedules"]["US"]["minute"]),(6,30))
        self.assertEqual((config["schedules"]["SG"]["hour"],config["schedules"]["SG"]["minute"]),(18,30))
        self.assertEqual(config["schedules"]["US"]["timezone"],"Asia/Singapore")
        self.store.save_notification_settings(NotificationSettings())
        self.assertEqual(configuration(self.store,self.provider,self.root)["regions"],[])

    def test_off_lines_and_disabled_signal_types_make_no_history_requests(self):
        self.store.set_notifications(self.line.id,"phone",False)
        before=len(self.client.calls)
        self.assertEqual(self.run_job()["status"],"disabled")
        self.assertEqual(len(self.client.calls),before)
        self.store.set_notifications(self.line.id,"phone",True)
        self.store.save_notification_settings(NotificationSettings())
        self.assertEqual(self.run_job()["status"],"disabled")
        self.assertEqual(len(self.client.calls),before)

    def test_region_gate_and_multiple_lines_share_one_download(self):
        self.store.save(self.us.key,self.provider.scenario,29,6)
        for line in self.store.list_all_lines(): self.store.set_notifications(line.id,"phone",True)
        self.store.save(self.sg.key,self.provider.scenario,9,6)
        sg=next(line for line in self.store.list_all_lines() if line.counter==self.sg.key)
        self.store.set_notifications(sg.id,"phone",True)
        report=self.run_job()
        self.assertEqual(report["checked"],2)
        self.assertEqual([call[1] for call in self.client.calls if call[0]=="history"],["AAPL"])

    def test_daily_claim_survives_restart_and_does_not_repeat_calls(self):
        first=self.run_job()
        calls=len(self.client.calls)
        fresh=LineStore(self.store.path)
        report=run_daily_notifications(fresh,self.provider,"US",self.phone,NOW)
        self.assertEqual(report["status"],"already_checked")
        self.assertEqual(len(self.client.calls),calls)
        self.assertEqual(first["checked"],1)

    def test_failed_fetch_attempts_only_once_and_logs_failure(self):
        self.client.failure=RuntimeError("403 Forbidden")
        self.assertEqual(self.run_job()["status"],"failed")
        calls=len(self.client.calls)
        self.assertEqual(self.run_job()["status"],"already_checked")
        self.assertEqual(len(self.client.calls),calls)
        self.phone.send.assert_not_called()

    def test_missing_expected_close_never_replays_a_prior_signal(self):
        self.client.bars=self.client.bars[:-1]
        report=self.run_job()
        self.assertEqual((report["checked"],report["posted"]),(0,0))
        self.phone.send.assert_not_called()
        self.assertTrue(any(e["status"]=="no_new_close" for e in self.provider.cache.diagnostic_events()))

    def test_global_and_line_switches_rechecked_after_a_slow_fetch(self):
        original=self.provider.historical_data
        def stop_during_fetch(*args,**kwargs):
            data=original(*args,**kwargs)
            self.store.set_notifications(self.line.id,"phone",False)
            return data
        with patch.object(self.provider,"historical_data",side_effect=stop_during_fetch):
            report=self.run_job()
        self.assertEqual(report["checked"],0)
        self.phone.send.assert_not_called()

    def test_global_signal_types_switched_off_during_fetch_prevent_delivery(self):
        original=self.provider.historical_data
        def stop_types(*args,**kwargs):
            data=original(*args,**kwargs)
            self.store.save_notification_settings(NotificationSettings())
            return data
        with patch.object(self.provider,"historical_data",side_effect=stop_types):
            self.assertEqual(self.run_job()["checked"],0)
        self.phone.send.assert_not_called()

    def test_concurrent_os_dispatches_claim_only_one_market_attempt(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            reports=list(executor.map(lambda _:self.run_job(),range(2)))
        self.assertEqual(sum(report["status"]=="already_checked" for report in reports),1)
        self.assertEqual(len([call for call in self.client.calls if call[0]=="history"]),1)

    def test_named_alerts_keep_delivery_identity_and_survive_hidden_lines(self):
        data=self.provider.historical_data(self.us)
        data=replace(data,prices=(14,12,10,8),dates=data.dates[-4:])
        line=self.store.get_line(self.line.id)
        unnamed=evaluate_dataset_eod(data,line,self.store.notification_settings())[0]
        self.store.rename(line.id,"Recovery watch")
        self.store.set_visible(line.id,False)
        named=evaluate_dataset_eod(data,self.store.get_line(line.id),self.store.notification_settings())[0]
        self.assertIn("Recovery watch",named.subject)
        self.assertIn("Recovery watch",named.body)
        self.assertNotIn("YAHOO",named.body)
        self.assertNotIn("YAHOO",named.subject)
        self.assertEqual(unnamed.key,named.key)
        with patch.object(self.provider,"historical_data",return_value=data):
            report=self.run_job()
        self.assertEqual(report["posted"],1)
        self.phone.send.assert_called_once()

    def test_disabled_email_and_preview_lines_never_schedule_delivery(self):
        self.store.save("DEMO-SGX","Trending",2,12)
        preview=next(line for line in self.store.list_all_lines() if line.counter=="DEMO-SGX")
        self.store.set_notifications(preview.id,"phone",True)
        self.assertEqual([line.counter for line,_ in enabled_lines(self.store,self.provider)],[self.us.key])

    def test_next_market_day_gets_a_new_claim_but_not_old_cached_signals(self):
        self.run_job()
        tomorrow=NOW+timedelta(days=1)
        self.provider.now=lambda:tomorrow
        result=self.run_job(now=tomorrow)
        self.assertNotEqual(result["status"],"already_checked")
        self.assertEqual(result["checked"],0)
