import json
import io
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

from sma_analyzer.desktop_yahoo import DesktopYahooClient, main
from sma_analyzer.yahoo import MarketDataError


class DesktopIsolationTests(unittest.TestCase):
    def test_worker_serializes_real_session_dates_and_timezone_aware_close_bounds(self):
        end=datetime(2026,11,5,21,tzinfo=timezone.utc)
        client=Mock()
        client.history.return_value=([{"date":"2026-11-04","close":123.0}],
                                     {"currentTradingPeriod":{"regular":{"end":end}}})
        request={"operation":"history","parameters":{"symbol":"AAPL","options":{"period":"max"}}}
        output=io.StringIO()
        with patch("sma_analyzer.desktop_yahoo.YFinanceClient",return_value=client), \
             patch("sys.stdin",io.StringIO(json.dumps(request))), \
             patch("sys.stdout",output), patch("sys.argv",["worker","/tmp/test-yf"]):
            main()
        response=json.loads(output.getvalue())
        self.assertTrue(response["ok"])
        self.assertEqual(response["value"][0][0]["date"],"2026-11-04")
        self.assertEqual(response["value"][1]["currentTradingPeriod"]["regular"]["end"],end.timestamp())

    @patch("sma_analyzer.desktop_yahoo.subprocess.run")
    def test_search_request_has_no_shell_and_decodes_worker_result(self, run):
        run.return_value = subprocess.CompletedProcess([],0,json.dumps(
            {"ok":True,"value":[{"symbol":"AAPL"}]}),"")
        client=DesktopYahooClient(Path("/tmp/test-yf"))
        self.assertEqual(client.search("Apple"),[{"symbol":"AAPL"}])
        options=run.call_args.kwargs
        self.assertNotIn("shell",options)
        self.assertEqual(json.loads(options["input"])["parameters"]["query"],"Apple")
        self.assertTrue(options["capture_output"])

    @patch("sma_analyzer.desktop_yahoo.subprocess.run")
    def test_os_kill_is_a_recoverable_error_and_stderr_is_not_exposed(self, run):
        run.return_value=subprocess.CompletedProcess([],-9,"","secret cookie or private path")
        with self.assertRaisesRegex(MarketDataError,"process was stopped") as raised:
            DesktopYahooClient("/tmp/test-yf").history("AAPL",period="max")
        self.assertNotIn("secret",str(raised.exception))
        self.assertIn("keep the file blocked",str(raised.exception))

    @patch("sma_analyzer.desktop_yahoo.subprocess.run")
    def test_worker_network_failure_is_reported_without_synthetic_fallback(self, run):
        run.return_value=subprocess.CompletedProcess([],0,json.dumps(
            {"ok":False,"message":"Yahoo data access was blocked."}),"")
        with self.assertRaisesRegex(MarketDataError,"access was blocked"):
            DesktopYahooClient("/tmp/test-yf").history("AAPL",period="max")

    @patch("sma_analyzer.desktop_yahoo.subprocess.run")
    def test_timeout_is_recoverable(self, run):
        run.side_effect=subprocess.TimeoutExpired("python",90)
        with self.assertRaisesRegex(MarketDataError,"timed out"):
            DesktopYahooClient("/tmp/test-yf").search("Apple")
