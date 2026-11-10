import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock,patch
import uuid

from service.alerts import run
from scripts.yahoo_test_data import FakeYahooClient,NOW
from sma_analyzer.market_cache import MarketCache
from sma_analyzer.storage import LineStore
from sma_analyzer.yahoo import YahooMarketDataProvider


class HeadlessServiceTests(TestCase):
    def setUp(self):
        temporary=TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.args={'directory':str(self.root),'run_id':str(uuid.uuid4()),'job':'US'}
        self.client=FakeYahooClient()
        self.provider=YahooMarketDataProvider(MarketCache(self.root/'market.sqlite3'),self.client,now=lambda:NOW)
        security=self.provider.search('apple')[0]
        self.store=LineStore(self.root/'saved_lines.sqlite3')
        self.store.save(security.key,self.provider.scenario,2,12)
        self.notifier=Mock()

    def execute(self,args=None,**kwargs):
        return run(args or self.args,provider_factory=lambda *_:self.provider,notifier=self.notifier,now=NOW,**kwargs)

    def result_file(self):
        return self.root/'notification-jobs'/(self.args['run_id']+'.json')

    def test_real_headless_job_returns_an_atomic_report_without_importing_kivy(self):
        with patch.dict('sys.modules',{'kivy':None,'sma_analyzer.app':None}):
            result=self.execute()
        self.assertEqual(result['status'],'ok')
        self.assertEqual(json.loads(self.result_file().read_text()),result)
        self.assertFalse(self.result_file().with_suffix('.tmp').exists())
        self.assertTrue(any(e['operation']=='notification-service' for e in self.provider.cache.diagnostic_events()))

    def test_provider_startup_failure_still_reports_stage_and_sanitized_error_type(self):
        result=run(self.args,provider_factory=Mock(side_effect=ImportError('private path token or account')),notifier=self.notifier)
        self.assertEqual((result['status'],result['stage'],result['error_type']),('failed','provider-startup','ImportError'))
        self.assertNotIn('private',self.result_file().read_text())

    def test_background_test_uses_no_market_api_or_saved_signal_and_posts_a_clear_test(self):
        calls=len(self.client.calls)
        result=self.execute(dict(self.args,test=True,job='TEST'))
        self.assertEqual((result['status'],result['checked'],result['posted']),('ok',0,1))
        self.assertEqual(len(self.client.calls),calls)
        alert=self.notifier.send.call_args.args[0]
        self.assertEqual(alert.kind,'test')
        self.assertIn('background',alert.subject)
        self.assertEqual(self.store.list_all_lines()[0].period,2)

    def test_cancelled_native_job_never_fetches_or_posts(self):
        marker=self.result_file().with_suffix('.cancel')
        marker.parent.mkdir(parents=True)
        marker.touch()
        calls=len(self.client.calls)
        self.assertEqual(self.execute()['status'],'failed')
        self.assertEqual(len(self.client.calls),calls)
        self.notifier.send.assert_not_called()

    def test_background_delivery_failure_is_reported_not_hidden_as_success(self):
        self.notifier.send.side_effect=RuntimeError('private device identifier')
        result=self.execute(dict(self.args,test=True,job='TEST'))
        self.assertEqual((result['status'],result['stage']),('failed','background-test-delivery'))
        self.assertNotIn('private device',json.dumps(self.provider.cache.diagnostic_events()))

    def test_old_queued_region_argument_is_accepted_after_upgrade(self):
        args=dict(self.args,region='US')
        args.pop('job')
        self.assertEqual(self.execute(args)['status'],'ok')
