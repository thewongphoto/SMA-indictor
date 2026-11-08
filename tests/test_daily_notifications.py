from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock,patch
from concurrent.futures import ThreadPoolExecutor

from scripts.yahoo_test_data import FakeYahooClient,NOW
from sma_analyzer.daily_notifications import run_daily_notifications,enabled_lines
from sma_analyzer.diagnostics import diagnostic_report
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
        self.store.save_notification_settings(NotificationSettings(phone_buy=False,phone_monitor=False))
        self.assertEqual(configuration(self.store,self.provider,self.root)["regions"],[])

    def test_native_expiry_stops_before_retrieval_and_does_not_replay_the_slot(self):
        before=len(self.client.calls)
        result=run_daily_notifications(self.store,self.provider,"US",self.phone,NOW,should_stop=lambda:True)
        self.assertEqual(result["status"],"failed")
        self.assertEqual(len(self.client.calls),before)
        self.phone.send.assert_not_called()
        self.assertEqual(self.run_job()["status"],"already_checked")

    def test_native_expiry_during_download_stops_before_signal_delivery(self):
        stopped=[False]
        original=self.provider.historical_data
        def fetch(*args,**kwargs):
            data=original(*args,**kwargs)
            stopped[0]=True
            return data
        with patch.object(self.provider,"historical_data",side_effect=fetch):
            result=run_daily_notifications(self.store,self.provider,"US",self.phone,NOW,should_stop=lambda:stopped[0])
        self.assertEqual(result["status"],"failed")
        self.phone.send.assert_not_called()

    def test_off_lines_and_disabled_signal_types_make_no_history_requests(self):
        self.store.set_notifications(self.line.id,"phone",False)
        before=len(self.client.calls)
        self.assertEqual(self.run_job()["status"],"disabled")
        self.assertEqual(len(self.client.calls),before)
        self.store.set_notifications(self.line.id,"phone",True)
        self.store.save_notification_settings(NotificationSettings(phone_buy=False,phone_monitor=False))
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
            self.store.save_notification_settings(NotificationSettings(phone_buy=False,phone_monitor=False))
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

    def signal_data(self, prices):
        data=self.provider.historical_data(self.us)
        return replace(data,prices=tuple(prices),dates=data.dates[-len(prices):])

    def assert_signal_log(self, prices, title):
        self.store.rename(self.line.id,"Recovery watch")
        data=self.signal_data(prices)
        with patch.object(self.provider,"historical_data",return_value=data):
            self.assertEqual(self.run_job()["posted"],1)
        events=self.provider.cache.diagnostic_events()
        for operation,status in (("notification-check","signal_match"),
                                 ("notification-trigger","triggered"),("notification-delivery","ok")):
            event=next(e for e in events if e["operation"]==operation and e["status"]==status)
            self.assertEqual(event["symbol"],"AAPL")
            for text in (title,"Recovery watch","SMA (2 days)","target 12/year",data.dates[-1]):
                self.assertIn(text,event["detail"])
        report=diagnostic_report(self.provider.cache,"android","Market data HTTPS",public_view=True)
        self.assertIn(title,report)
        self.assertIn("OS accepted the notification",report)
        self.assertNotIn("yahoo",report.lower())

    def test_buy_trigger_and_delivery_log_identify_saved_line_and_date(self):
        self.assert_signal_log((10,12,10,12),"Buy signal")

    def test_impending_trigger_and_delivery_log_identify_saved_line_and_date(self):
        self.assert_signal_log((14,12,10,8),"Impending buy signal")

    def test_duplicate_signal_logs_suppression_without_new_trigger_or_post(self):
        data=self.signal_data((14,12,10,8))
        alert,=evaluate_dataset_eod(data,self.store.get_line(self.line.id),self.store.notification_settings())
        self.store.record_delivery(alert.key)
        with patch.object(self.provider,"historical_data",return_value=data):
            self.assertEqual(self.run_job()["posted"],0)
        self.phone.send.assert_not_called()
        events=self.provider.cache.diagnostic_events()
        duplicate=next(e for e in events if e["operation"]=="notification-delivery")
        self.assertEqual(duplicate["status"],"already_delivered")
        self.assertIn("Impending buy signal",duplicate["detail"])
        self.assertIn("Duplicate suppressed",duplicate["detail"])
        self.assertFalse(any(e["operation"]=="notification-trigger" for e in events))

    def test_nonmatching_check_lists_types_without_claiming_a_trigger(self):
        data=self.signal_data((10,12,14,16))
        with patch.object(self.provider,"historical_data",return_value=data):
            self.assertEqual(self.run_job()["posted"],0)
        event=next(e for e in self.provider.cache.diagnostic_events() if e["operation"]=="notification-check")
        self.assertEqual(event["status"],"no_signal")
        self.assertIn("Buy signal On; Impending buy signal On",event["detail"])
        self.phone.send.assert_not_called()

    def test_delivery_failure_keeps_signal_context_and_excludes_raw_errors(self):
        data=self.signal_data((14,12,10,8))
        raw_error="private device details not for logs"
        self.phone.send.side_effect=RuntimeError(raw_error)
        with patch.object(self.provider,"historical_data",return_value=data):
            self.assertEqual(self.run_job()["status"],"failed")
        event=next(e for e in self.provider.cache.diagnostic_events() if e["operation"]=="notification-delivery")
        self.assertEqual(event["status"],"failed")
        self.assertIn("Impending buy signal",event["detail"])
        self.assertIn(data.dates[-1],event["detail"])
        self.assertNotIn(raw_error,diagnostic_report(self.provider.cache,"android","Market data HTTPS"))
        self.provider.cache.clear_downloads()
        reopened=MarketCache(self.provider.cache.path)
        self.assertTrue(any(e["operation"]=="notification-delivery" for e in reopened.diagnostic_events()))

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
