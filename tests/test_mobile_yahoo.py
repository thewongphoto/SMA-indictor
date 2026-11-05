"""Fictional Yahoo JSON responses; no network or real licensed histories."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from scripts.yahoo_test_data import FakeYahooClient, NOW, bars_ending
from sma_analyzer.diagnostics import diagnostic_report
from sma_analyzer.market_cache import MarketCache
from sma_analyzer.mobile_yahoo import YahooJSONClient, YahooHTTPError, parse_chart, CHART, SEARCH, COOKIE, CRUMB
from sma_analyzer.providers import create_provider
from sma_analyzer.yahoo import MarketDataError, YahooMarketDataProvider


from scripts.yahoo_json_test_data import chart_payload, Response, Session


class MobileYahooTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.cache=MarketCache(self.root/"market.sqlite3")

    def client(self,session):
        client=YahooJSONClient(self.root,session=session,observer=self.cache.operation,now=lambda:NOW)
        client.begin_operation("test-id","history","AAPL")
        return client

    def test_parser_preserves_exchange_dates_nulls_close_adjustment_and_actions(self):
        bars=bars_ending(count=5)
        bars[1]["close"]=None
        bars[2]["dividends"]=.5
        bars[3]["splits"]=4.
        payload=chart_payload(bars,"D05.SI")
        parsed,metadata=parse_chart(payload)
        self.assertEqual(parsed,bars)
        self.assertEqual(metadata["exchangeTimezoneName"],"Asia/Singapore")

    def test_parser_does_not_accept_monthly_data_or_mismatched_arrays_as_daily_history(self):
        payload=chart_payload()
        payload["chart"]["result"][0]["meta"]["dataGranularity"]="1mo"
        with self.assertRaisesRegex(MarketDataError,"daily"):
            parse_chart(payload)
        payload=chart_payload()
        payload["chart"]["result"][0]["indicators"]["quote"][0]["close"].pop()
        with self.assertRaisesRegex(MarketDataError,"incomplete"):
            parse_chart(payload)

    def test_search_is_one_request_with_no_news_and_no_certificate_bypass(self):
        session=Session(Response(payload={"quotes":[{"symbol":"AAPL"}]}))
        quotes=self.client(session).search("apple")
        self.assertEqual(quotes,[{"symbol":"AAPL"}])
        self.assertEqual(len(session.calls),1)
        url,options=session.calls[0]
        self.assertEqual(url,SEARCH)
        self.assertEqual(options["params"]["newsCount"],0)
        self.assertTrue(options["verify"])
        self.assertFalse(options["allow_redirects"])

    def test_full_daily_history_uses_full_bounds_and_health_uses_five_days(self):
        session=Session(Response(payload=chart_payload()),Response(payload=chart_payload(symbol="SPY")))
        client=self.client(session)
        bars,_=client.history("AAPL",period="max")
        self.assertEqual(len(bars),5)
        self.assertLess(session.calls[0][1]["params"]["period1"],0)
        self.assertNotIn("range",session.calls[0][1]["params"])
        self.assertEqual(session.calls[0][1]["params"]["includeAdjustedClose"],"true")
        client.history("SPY",period="5d")
        self.assertEqual(session.calls[1][1]["params"]["range"],"5d")

    def test_history_cannot_be_attributed_to_the_wrong_company(self):
        with self.assertRaisesRegex(MarketDataError,"different security"):
            self.client(Session(Response(payload=chart_payload(symbol="MSFT")))).history("AAPL",period="max")

    def test_incremental_start_is_inclusive_exchange_midnight(self):
        session=Session(Response(payload=chart_payload(symbol="D05.SI")))
        self.client(session).history("D05.SI",start="2026-10-25")
        stamp=session.calls[0][1]["params"]["period1"]
        self.assertEqual(datetime.fromtimestamp(stamp,timezone.utc).isoformat(),"2026-10-24T16:00:00+00:00")

    def test_one_standard_401_recovery_and_no_secrets_in_http_log(self):
        session=Session(Response(401,text="private response"),
                        Response(404,text="private cookie setup",headers={"Set-Cookie":"secret-cookie"}),
                        Response(text="secret-crumb"),Response(payload={"quotes":[]}))
        self.assertEqual(self.client(session).search("apple"),[])
        self.assertEqual([url for url,_ in session.calls],[SEARCH,COOKIE,CRUMB,SEARCH])
        self.assertEqual(session.calls[-1][1]["params"]["crumb"],"secret-crumb")
        report=diagnostic_report(self.cache,"android","Yahoo HTTPS")
        self.assertIn("HTTP 401",report)
        self.assertIn("HTTP 404",report)
        self.assertNotIn("secret-crumb",report)
        self.assertNotIn("secret-cookie",report)
        self.assertNotIn("private response",report)

    def test_invalid_session_response_is_not_reused_as_a_crumb(self):
        session=Session(Response(401),Response(404),Response(text='{"secret":"not-a-crumb"}'))
        with self.assertRaisesRegex(MarketDataError,"anonymous data session"):
            self.client(session).search("apple")
        self.assertEqual(len(session.calls),3)
        self.assertNotIn("not-a-crumb",diagnostic_report(self.cache,"android","Yahoo HTTPS"))

    def test_403_and_429_are_not_retried_and_rate_limit_is_persisted(self):
        for status in (403,429):
            with self.subTest(status=status):
                session=Session(Response(status,text="do not expose this body",headers={"Retry-After":"300"}))
                client=self.client(session)
                provider=YahooMarketDataProvider(self.cache,client=client,now=lambda:NOW)
                ok,warning=provider.health_check()
                self.assertFalse(ok)
                self.assertEqual(len(session.calls),1)
                self.assertNotIn("expose",warning)
                self.assertEqual(self.cache.diagnostic_events(1)[0]["http_status"],status)
                if status==429:
                    self.assertGreaterEqual(self.cache.preference("yahoo_retry_at"),NOW.timestamp()+300)

    def test_failed_real_transport_preserves_existing_persistent_prices(self):
        fake=FakeYahooClient()
        provider=YahooMarketDataProvider(self.cache,client=fake,now=lambda:NOW)
        security=provider.search("apple")[0]
        before=provider.historical_data(security)
        provider._client=self.client(Session(Response(503,text="private server body")))
        after=provider.historical_data(security,force=True)
        self.assertEqual(after.prices,before.prices)
        self.assertTrue(after.stale)
        report=diagnostic_report(self.cache,"android","Yahoo HTTPS",after)
        self.assertIn("HTTP 503",report)
        self.assertIn("stale=True",report)
        self.assertNotIn("private server body",report)

    def test_invalid_json_and_finance_symbol_error_are_visible_failures(self):
        with self.assertRaisesRegex(MarketDataError,"invalid data response"):
            self.client(Session(Response(text="<html>blocked</html>"))).search("apple")
        payload={"chart":{"error":{"code":"Not Found"},"result":None}}
        with self.assertRaisesRegex(MarketDataError,"symbol/history"):
            parse_chart(payload)

    def test_android_and_ios_factory_need_no_desktop_native_dependencies(self):
        with patch.dict("sys.modules",{name:None for name in ("yfinance","pandas","numpy","curl_cffi")}):
            for platform in ("android","ios"):
                provider=create_provider(self.root/platform,platform)
                client=provider.client_factory(self.root/platform/"state")
                self.assertIsInstance(client,YahooJSONClient)
                self.assertEqual(provider.initial_dataset().prices,())
                self.assertIn("mobile",provider.transport_name)

    def test_existing_log_schema_is_upgraded_without_losing_old_events(self):
        path=self.root/"old.sqlite3"
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE market_operations(id INTEGER PRIMARY KEY,at REAL,operation TEXT,"
                       "symbol TEXT,status TEXT,detail TEXT)")
            db.execute("INSERT INTO market_operations VALUES (1,0,'health','SPY','ok','old')")
        cache=MarketCache(path)
        self.assertEqual(cache.operations()[0][4],"old")
        self.assertEqual(cache.diagnostic_events()[0]["endpoint"],"")
        cache.operation("http","SPY","failed",request_id="id",http_status=403,duration_ms=20,
                        endpoint="https://user:pass@query2.finance.yahoo.com/v8/chart?crumb=SECRET#fragment")
        report=diagnostic_report(cache,"android","Yahoo HTTPS")
        self.assertIn("HTTP 403",report)
        self.assertIn("query2.finance.yahoo.com/v8/chart",report)
        self.assertNotIn("SECRET",report)
        self.assertNotIn("user:pass",report)

    def test_log_reports_cache_hits_separately_from_network(self):
        fake=FakeYahooClient()
        provider=YahooMarketDataProvider(self.cache,client=fake,now=lambda:NOW)
        provider.search("apple")
        before=len(fake.calls)
        provider.search("apple")
        report=diagnostic_report(self.cache,"android","Yahoo HTTPS")
        self.assertEqual(len(fake.calls),before)
        self.assertIn("[CACHE",report)
        self.assertIn("cache_hit",report)
