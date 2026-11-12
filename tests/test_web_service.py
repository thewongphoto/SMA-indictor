"""Production model parity and private web API persistence regressions."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import time

from web_worker.service import Service
from sma_analyzer.engine import optimize_sma
from sma_analyzer.palette import line_color


class WebServiceTests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.service=Service(Path(self.tmp.name),preview=True)
        self.key='NASDAQ:AAPL'

    def tearDown(self):
        self.service.executor.shutdown(wait=True)
        self.tmp.cleanup()

    def call(self,path,body=None,method=None):
        return self.service.handle(method or ('GET' if path in ('state','log','contact-capabilities') or path.startswith('jobs/') else 'POST'),path,body or {})

    def result(self):
        job=self.call('optimize',{'key':self.key,'target':4})['job']
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            value=self.call('jobs/'+job,method='GET')
            if value['status']!='running':
                self.assertEqual(value['status'],'complete',value)
                return value['data']
            time.sleep(.01)
        self.fail('Calculation did not complete')

    def test_engine_parity_and_saved_identity_round_trip(self):
        chart=self.result()
        expected=optimize_sma(chart['prices'],4)
        self.assertEqual(chart['result']['period'],expected.period)
        self.assertEqual(chart['result']['frequency'],expected.actual_annual_frequency)
        self.assertEqual([len(row['indices']) for row in chart['backtest']['rows']],
                         [len(chart['result']['events'])]*3)
        args=dict(key=self.key,period=expected.period,target=4)
        state=self.call('save',args)
        line=state['cards'][0]['lines'][0]
        state=self.call('line',dict(id=line['id'],name='Long-term trend',color=2,visible=False,push_enabled=True))
        self.assertFalse(state['cards'][0]['lines'][0]['visible'])
        self.assertTrue(state['cards'][0]['lines'][0]['push_enabled'])
        saved=state['cards'][0]['lines'][0]
        self.assertTrue(saved['alert_buy'] and saved['alert_monitor'] and saved['alert_start'])
        state=self.call('line',dict(id=line['id'],alert_buy=False,alert_start=False))
        saved=state['cards'][0]['lines'][0]
        self.assertEqual((saved['alert_buy'],saved['alert_monitor'],saved['alert_start']),(False,True,False))
        self.assertEqual(state['cards'][0]['lines'][0]['color'],-3)
        self.call('line',dict(id=line['id'],archive=True))
        archive=self.call('state')['archive'][0]
        restored=self.call('restore',{'id':archive['id']})['cards'][0]['lines'][0]
        self.assertEqual(restored['custom_name'],'Long-term trend')
        self.assertEqual(restored['period'],expected.period)
        self.assertEqual(restored['color'],-3)
        self.service.executor.shutdown(wait=True)
        self.service=Service(Path(self.tmp.name),preview=True)
        self.assertEqual(self.call('state')['cards'][0]['lines'][0]['custom_name'],'Long-term trend')

    def test_watchlist_does_not_retrieve_history(self):
        self.call('save',dict(key=self.key,period=50,target=4))
        with patch.object(self.service.model.data_provider,'historical_data',side_effect=AssertionError('unexpected fetch')):
            card=self.call('state')['cards'][0]
        self.assertIsNotNone(card['price'])
        self.assertIn(next(iter(card['states'].values())),('Above','Below','On line'))

    def test_invalid_frequency_and_unknown_jobs(self):
        for target in (0,-1,2.5,True):
            with self.assertRaises(ValueError):self.call('optimize',dict(key=self.key,target=target))
        with self.assertRaises(ValueError):self.call('jobs/missing')
        with self.assertRaises(ValueError):self.call('clear-cache',method='GET')

    def test_preview_never_enables_email(self):
        with patch('web_worker.contact.enabled',return_value=True),patch('web_worker.contact.send') as send:
            self.assertFalse(self.call('contact-capabilities')['enabled'])
            with self.assertRaises(ValueError):self.call('contact-email',{'email':'example@example.com'})
            send.assert_not_called()

    def test_native_and_web_colors_share_automatic_palette(self):
        for period in range(2,15):
            self.call('save',dict(key=self.key,period=period,target=4))
        lines=self.call('state')['cards'][0]['lines']
        self.assertEqual(len(lines),13)
        for line in lines:
            expected='#'+''.join(f'{round(v*255):02x}' for v in line_color(line['color'])[:3])
            self.assertEqual(line['color_hex'],expected)
