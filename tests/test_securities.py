from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from sma_analyzer.market_data import PreviewMarketDataProvider
from sma_analyzer.mock_data import generate_mock_data
from sma_analyzer.model import AnalyzerModel
from sma_analyzer.securities import SECURITIES, normalize_query, search_securities, security_by_key
from sma_analyzer.storage import LineStore


class SecuritySearchTests(unittest.TestCase):
    def test_partial_ticker_and_company_names_are_case_insensitive(self):
        self.assertEqual(search_securities('aa')[0].ticker, 'AAPL')
        self.assertEqual(search_securities('app')[0].name, 'Apple Inc.')
        self.assertEqual(search_securities('MICRO')[0].ticker, 'MSFT')
        self.assertEqual(search_securities('bank')[0].exchange, 'SGX')
        self.assertEqual(search_securities('DBS')[0].ticker, 'D05')
        self.assertEqual(search_securities('singapore air')[0].ticker, 'C6L')
        self.assertEqual(search_securities('  ＡＡＰＬ  ')[0].ticker, 'AAPL')

    def test_empty_unknown_and_too_long_queries(self):
        self.assertEqual(search_securities('   '), ())
        self.assertEqual(search_securities('no-such-counter-123'), ())
        with self.assertRaises(ValueError):
            normalize_query('a' * 129)
        with self.assertRaises(ValueError):
            normalize_query(None)

    def test_identity_exchange_and_logo_metadata_are_stable(self):
        self.assertEqual(len({item.key for item in SECURITIES}), len(SECURITIES))
        for item in SECURITIES:
            self.assertIs(security_by_key(item.key), item)
            self.assertTrue(item.ticker and item.name and item.exchange and item.initials)
            if item.logo:
                self.assertTrue(Path(item.logo_path).is_file())
        self.assertTrue(security_by_key('SGX:D05').logo_path.endswith('dbs.png'))
        with self.assertRaises(ValueError):
            security_by_key('UNKNOWN')

    def test_preview_search_and_history_make_no_network_requests(self):
        provider = PreviewMarketDataProvider()
        with patch('urllib.request.urlopen', side_effect=AssertionError('No preview network calls')):
            result = provider.search('Apple')[0]
            data = provider.historical_data(result, 'Trending')
        self.assertEqual(data.counter, 'NASDAQ:AAPL')
        self.assertEqual(len(data.prices), 1260)
        self.assertIn('SIMULATED', data.label)
        self.assertEqual(provider.historical_data(result, 'Trending'), data)

    def test_existing_mock_series_remain_identical(self):
        provider = PreviewMarketDataProvider()
        for counter in ('DEMO-SGX', 'DEMO-US'):
            for scenario in ('Trending', 'Oscillating', 'Sideways'):
                self.assertEqual(provider.historical_data(security_by_key(counter), scenario),
                                 generate_mock_data(counter, scenario))

    def test_new_securities_restore_saved_parameters_with_same_provider(self):
        with TemporaryDirectory() as directory:
            store = LineStore(Path(directory)/'saved.sqlite3')
            model = AnalyzerModel(store)
            model.select_dataset('NASDAQ:AAPL', 'Trending')
            data = model.dataset
            store.save(data.counter, data.scenario, 11, 12)
            line = store.list_all_lines()[0]
            model.select_dataset('SGX:D05', 'Sideways')
            model.view_saved_line(line.id)
            self.assertEqual(model.dataset, data)
            self.assertEqual(model.result.period, 11)
            self.assertTrue(model.viewing_saved)

    def test_failed_history_selection_preserves_existing_analysis(self):
        with TemporaryDirectory() as directory:
            provider = PreviewMarketDataProvider()
            model = AnalyzerModel(LineStore(Path(directory)/'saved.sqlite3'), provider)
            previous = model.dataset
            with patch.object(provider, 'historical_data', side_effect=ValueError('Unavailable')):
                with self.assertRaises(ValueError):
                    model.select_dataset('NASDAQ:AAPL', 'Trending')
            self.assertIs(model.dataset, previous)
