from dataclasses import replace
from datetime import datetime,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock,patch

from scripts.yahoo_test_data import FakeYahooClient,NOW
from sma_analyzer.daily_notifications import run_daily_notifications
from sma_analyzer.market_cache import MarketCache
from sma_analyzer.native_schedule import configuration
from sma_analyzer.notifications import NotificationSettings,evaluate_dataset_start,evaluate_dataset_eod
from sma_analyzer.schedule import SGT,schedule_spec,latest_due,next_due,expected_session_date
from sma_analyzer.storage import LineStore
from sma_analyzer.yahoo import YahooMarketDataProvider


class OpeningNotificationsTests(TestCase):
    def setUp(self):
        temporary=TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.store=LineStore(self.root/'saved_lines.sqlite3')
        self.client=FakeYahooClient()
        self.client.bars=self.client.bars[-4:]
        for bar,price in zip(self.client.bars,(10,12,14,16)):
            bar.update(close=price,adj_close=price)
        self.provider=YahooMarketDataProvider(MarketCache(self.root/'market.sqlite3'),self.client,now=lambda:NOW)
        self.security=self.provider.search('apple')[0]
        self.data=self.provider.historical_data(self.security)
        self.store.save(self.security.key,self.provider.scenario,2,12)
        self.line=self.store.list_all_lines()[0]
        self.phone=Mock()
        self.now=datetime(2026,11,5,21,30,tzinfo=SGT)

    def start(self,**kwargs):
        return run_daily_notifications(self.store,self.provider,'US',self.phone,self.now,phase='start',**kwargs)

    def test_fixed_singapore_opening_times_weekdays_dst_and_weekend_reference(self):
        self.assertEqual(schedule_spec('US','start'),(21,30,{0,1,2,3,4}))
        self.assertEqual(schedule_spec('SG','start'),(9,0,{0,1,2,3,4}))
        for month in (1,7,11):
            due=next_due('US',datetime(2026,month,15,0,0,tzinfo=SGT),'start')
            self.assertEqual((due.hour,due.minute),(21,30))
            self.assertLess(due.weekday(),5)
        monday=datetime(2026,11,9,21,30,tzinfo=SGT)
        self.assertEqual(expected_session_date('US',monday,'start').isoformat(),'2026-11-06')
        self.assertEqual(expected_session_date('SG',monday.replace(hour=9,minute=0),'start').isoformat(),'2026-11-06')

    def test_requested_above_sma_condition_exact_message_and_off_gates(self):
        settings=NotificationSettings()
        alert,=evaluate_dataset_start(self.data,self.line,settings,'2026-11-05',self.security.name,'US')
        self.assertEqual(alert.kind,'monitor_start')
        self.assertEqual(alert.body,'US trading is starting soon! SMA (2 days) for Apple Inc. may cross today. App does not feature live prices, so monitor online.')
        self.assertEqual(alert.reference_date,'2026-11-04')
        self.assertEqual(alert.session_date,'2026-11-05')
        self.assertIn('Impending buy signal (Start of trading)',alert.subject)
        for prices in ((16,14,12,10),(10,10,10,10),(10,12,14,None)):
            self.assertEqual(evaluate_dataset_start(replace(self.data,prices=prices),self.line,settings,'2026-11-05','Apple Inc.','US'),())
        self.assertEqual(evaluate_dataset_start(self.data,replace(self.line,push_enabled=False),settings,'2026-11-05','Apple Inc.','US'),())
        self.assertEqual(evaluate_dataset_start(self.data,self.line,replace(settings,phone_monitor_start=False),'2026-11-05','Apple Inc.','US'),())
        self.assertEqual(evaluate_dataset_start(self.data,replace(self.line,period=20),settings,'2026-11-05','Apple Inc.','US'),())

    def test_sgx_name_custom_sma_and_distinct_event_identity(self):
        custom=replace(self.line,custom_name='Recovery')
        first,=evaluate_dataset_start(self.data,custom,NotificationSettings(),'2026-11-05','DBS Group Holdings Ltd','SG')
        second,=evaluate_dataset_start(self.data,custom,NotificationSettings(),'2026-11-06','DBS Group Holdings Ltd','SG')
        self.assertTrue(first.body.startswith('SGX trading is starting soon! Recovery · SMA (2 days) for DBS Group Holdings Ltd'))
        self.assertNotEqual(first.key,second.key)
        falling=replace(self.data,prices=(16,14,12,10))
        end,=evaluate_dataset_eod(falling,self.line,NotificationSettings())
        self.assertIn('Impending buy signal (End of trading)',end.subject)
        self.assertNotEqual(first.key,end.key)

    def test_opening_job_reads_cache_without_network_and_deduplicates_across_restart(self):
        calls=len(self.client.calls)
        with patch.object(self.provider,'historical_data',side_effect=AssertionError('Opening alerts must not call the API')):
            result=self.start()
        self.assertEqual((result['status'],result['checked'],result['posted']),('ok',1,1))
        self.assertEqual(len(self.client.calls),calls)
        self.phone.send.assert_called_once()
        self.store=LineStore(self.store.path)
        self.assertEqual(self.start()['status'],'already_checked')
        self.phone.send.assert_called_once()
        log=' '.join(e['detail'] for e in self.provider.cache.diagnostic_events())
        self.assertIn('Impending buy signal (Start of trading)',log)
        self.assertIn('previous close 2026-11-04',log)

    def test_start_only_preference_still_refreshes_at_close_then_sends_at_open(self):
        self.store.save_notification_settings(NotificationSettings(phone_buy=False,phone_monitor=False,phone_monitor_start=True))
        config=configuration(self.store,self.provider,self.root)
        self.assertEqual(set(config['jobs']),{'US','US_START'})
        result=run_daily_notifications(self.store,self.provider,'US',self.phone,NOW)
        self.assertEqual(result['status'],'ok')
        self.phone.send.assert_not_called()
        self.assertEqual(self.start()['posted'],1)

    def test_no_open_job_when_type_off_and_no_jobs_when_all_types_off(self):
        self.store.save_notification_settings(NotificationSettings(phone_monitor_start=False))
        self.assertEqual(configuration(self.store,self.provider,self.root)['jobs'],['US'])
        self.assertEqual(self.start()['status'],'disabled')
        self.store.save_notification_settings(NotificationSettings(phone_buy=False,phone_monitor=False,phone_monitor_start=False))
        self.assertEqual(configuration(self.store,self.provider,self.root)['jobs'],[])

    def test_expired_opening_or_older_native_slot_never_fetches_or_posts(self):
        self.now+=timedelta(minutes=31)
        calls=len(self.client.calls)
        self.assertEqual(self.start()['status'],'expired')
        self.now-=timedelta(minutes=31)
        yesterday=self.now-timedelta(days=1)
        self.assertEqual(self.start(due_at=yesterday.timestamp())['status'],'expired')
        self.assertEqual(len(self.client.calls),calls)
        self.phone.send.assert_not_called()

    def test_exact_due_timestamp_uses_singapore_trading_date(self):
        self.assertEqual(self.start(due_at=self.now.timestamp())['posted'],1)
        self.assertEqual(self.phone.send.call_args.args[0].session_date,'2026-11-05')

    def test_new_type_disabled_during_cached_read_prevents_delivery(self):
        cached=self.provider.cached_data
        def disable(security):
            data=cached(security)
            self.store.save_notification_settings(NotificationSettings(phone_monitor_start=False))
            return data
        with patch.object(self.provider,'cached_data',side_effect=disable):
            self.assertEqual(self.start()['checked'],0)
        self.phone.send.assert_not_called()

    def test_stale_history_is_rejected_but_recently_verified_holiday_close_is_usable(self):
        older=replace(self.data,dates=('2026-10-29','2026-10-30','2026-11-02','2026-11-03'),
                      fetched_at=(self.now-timedelta(days=2)).timestamp())
        with patch.object(self.provider,'cached_data',return_value=older):
            self.assertEqual(self.start()['checked'],0)
        self.phone.send.assert_not_called()
        # A new slot after a fresh closing check can establish that there was
        # no newer close (weekday holiday), rather than replaying a stale cache.
        self.now+=timedelta(days=1)
        verified=replace(older,fetched_at=self.now.timestamp())
        with patch.object(self.provider,'cached_data',return_value=verified):
            self.assertEqual(self.start()['posted'],1)
