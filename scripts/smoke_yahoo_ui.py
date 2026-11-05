"""Running-widget integration test with a recorded synthetic transport, never Yahoo."""
import json
import os
from pathlib import Path
import tempfile
import time
import traceback
import subprocess
from unittest.mock import patch

temporary = tempfile.TemporaryDirectory(prefix="sma-yahoo-ui-")
os.environ["SMA_ANALYZER_DATA_DIR"] = temporary.name
os.environ["SMA_DATA_SOURCE"] = "preview"
for key in ("KIVY_HOME", "XDG_CACHE_HOME"):
    if os.environ.get(key):
        Path(os.environ[key]).mkdir(parents=True, exist_ok=True)

from kivy.app import App
from kivy.clock import Clock
from scripts.yahoo_test_data import FakeYahooClient, NOW
from sma_analyzer.app import AnalyzerScreen
from sma_analyzer.market_cache import MarketCache
from sma_analyzer.model import AnalyzerModel
from sma_analyzer.storage import LineStore
from sma_analyzer.yahoo import YahooMarketDataProvider
from sma_analyzer.desktop_yahoo import DesktopYahooClient


class YahooSmoke(App):
    title = "Yahoo desktop UI · synthetic transport test"
    failed = False

    def build(self):
        root = Path(temporary.name)
        self.client = FakeYahooClient()
        self.cache = MarketCache(root/"market_data.sqlite3")
        self.provider = YahooMarketDataProvider(self.cache,self.client,now=lambda:NOW)
        store = LineStore(root/"saved_lines.sqlite3")
        store.save("DEMO-SGX","Oscillating",20,12)
        self.screen = AnalyzerScreen(AnalyzerModel(store,self.provider))
        self.checks = []
        return self.screen

    def on_start(self):
        self.sequence = self.steps()
        self.condition = lambda: True
        self.deadline = time.monotonic()+30
        Clock.schedule_interval(self.tick,.05)

    def checked(self, name):
        self.checks.append(name)

    def tick(self, *_):
        try:
            if not self.condition():
                if time.monotonic() > self.deadline:
                    raise TimeoutError("UI test step timed out.")
                return
            self.condition = next(self.sequence)
            self.deadline = time.monotonic()+30
        except StopIteration:
            self.stop()
            return False
        except Exception:
            self.failed = True
            traceback.print_exc()
            self.stop()
            return False

    def steps(self):
        ui = self.screen
        assert ui.model.dataset.counter=="UNSELECTED"
        assert ui.model.dataset.prices==()
        assert ui.counter.security.name=="Choose a company"
        assert ui.library_state=="empty"
        assert ui.saved_rows=={} and ui.landing_saved_rows=={}
        self.checked("live start has no demo selection or imported synthetic library rows")
        yield lambda:not ui._source_check_busy
        assert self.client.calls == [("history","SPY",{"period":"5d"})]
        assert ui.source_warning.text == ""
        self.checked("one quiet startup check")
        ui.show_search()
        ui.security_search.text = "apple"
        before = len(self.client.calls)
        yield lambda:True
        assert len(self.client.calls) == before
        self.checked("typing makes no calls")
        ui.submit_security_search()
        yield lambda:not ui.search_busy
        assert len(ui.search_results)==1
        assert self.client.calls[-1][0]=="search"
        self.checked("submitted search")
        ui.select_security_match(ui.search_results[0])
        yield lambda:not ui.history_loading
        assert ui.manager.current=="parameters", ui.search_status.text
        assert ui.model.dataset.counter=="YAHOO:AAPL"
        assert len(ui.model.dataset.prices)==1700
        assert ui.model.dataset.prices==tuple(b["adj_close"] for b in self.client.bars)
        assert ui.chart.prices==ui.model.dataset.prices
        assert ui.scenario_cell.parent is None
        self.checked("full real-date provider result and no fictional pattern controls")
        ui.on_optimize()
        yield lambda:not ui.busy
        assert ui.model.result is not None, ui.status.text
        assert ui.manager.current=="results"
        assert ui.plot_title.security.name=="Apple Inc."
        assert "USD adjusted daily close" in ui.plot_subtitle.text
        assert "Dividends/splits included" in ui.plot_subtitle.text
        assert ui.chart.price_label=="Adj. close"
        assert "yahoo" not in ui.plot_subtitle.text.lower()
        ui.chart.set_timeline("Max")
        assert tuple(ui.chart.view_range)==(0,1699)
        self.checked("long-history optimization and full MAX chart")
        ui.backtest_period._dropdown.select("Max")
        assert ui.backtest_values["crossings"].text.startswith("USD ")
        assert ui.backtest_report.end==1699
        self.checked("currency and calendar backtest")
        calls = len(self.client.calls)
        ui.on_save()
        line = ui.model.current_saved_line()
        assert line is not None
        period=line.period
        ui.saved_sheet.dismiss()
        ui.show_library()
        ui.on_view_saved(line)
        yield lambda:not ui.history_loading
        assert ui.model.result.period==period
        assert len(self.client.calls)==calls
        assert ui.model.viewing_saved
        self.checked("saved View shares cache and preserves period")
        ui.show_settings()
        assert ui.phone_test_button.disabled and ui.eod_deliver_button.disabled
        ui.refresh_current_prices()
        yield lambda:not ui.history_loading
        assert len(self.client.calls)==calls+1
        assert ui.model.result.period==period
        assert self.client.calls[-1][2].get("start")
        self.checked("explicit incremental refresh, mobile tests deferred")
        self.client.failure=RuntimeError("403 Forbidden")
        ui.refresh_current_prices()
        yield lambda:not ui.history_loading
        assert ui.model.dataset.stale
        assert len(ui.model.dataset.prices)==1700
        assert "Saved data" in ui.plot_subtitle.text
        self.checked("failed request retains chart and marks stale")
        previous = self.provider._client
        self.provider._client = DesktopYahooClient(Path(temporary.name)/"yfinance-state")
        with patch("sma_analyzer.desktop_yahoo.subprocess.run",
                   return_value=subprocess.CompletedProcess([],-9,"","private OS diagnostic")):
            ui.check_yahoo_source(force=True)
            yield lambda:not ui._source_check_busy
            assert "process was stopped" in ui.source_warning.text
            assert ui.model.dataset.counter=="YAHOO:AAPL"
            assert len(ui.model.dataset.prices)==1700
            assert not ui.closed
        self.provider._client = previous
        self.checked("OS-killed Yahoo support process leaves live Kivy chart open")
        assert not any(name.startswith("desktop-worker") for name in os.listdir(temporary.name))
        self.checked("no desktop background worker")
        ui.confirm_clear_market_data()
        clear = next(widget for widget in ui.clear_data_popup.content.children
                     if getattr(widget,"text","")=="Clear downloaded data")
        clear.dispatch("on_release")
        assert ui.model.dataset.counter=="UNSELECTED"
        assert ui.model.dataset.prices==()
        assert len(ui.model.library_lines())==1
        assert len(ui.model.store.list_all_lines())==2
        self.checked("clear cache keeps real saved parameters and resets to unselected live state")

    def on_stop(self):
        self.screen.close()
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/yahoo-ui-smoke.json").write_text(json.dumps(
            {"passed":not self.failed,"checks":self.checks,"transport":"synthetic fixture; no live Yahoo calls"},indent=2))


if __name__ == "__main__":
    app=YahooSmoke()
    app.run()
    temporary.cleanup()
    raise SystemExit(1 if app.failed else 0)
