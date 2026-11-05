"""Exercise the actual mobile HTTPS/parser/cache/UI path using synthetic JSON."""
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import unquote
from unittest.mock import patch
from zoneinfo import ZoneInfo

from scripts.smoke_yahoo_ui import YahooSmoke, temporary
from scripts.yahoo_test_data import FakeYahooClient, NOW
from scripts.yahoo_json_test_data import Response, chart_payload
from sma_analyzer.app import AnalyzerScreen
from sma_analyzer.model import AnalyzerModel
from sma_analyzer.storage import LineStore
from sma_analyzer.providers import create_provider
from sma_analyzer.mobile_yahoo import YahooJSONClient, SEARCH, CHART


class RoutedSession:
    def __init__(self, source):
        self.source=source
        self.headers={}

    def get(self,url,params=None,**kwargs):
        if url == SEARCH:
            return Response(payload={"quotes":self.source.search(params["q"])})
        assert url.startswith(CHART)
        symbol=unquote(url[len(CHART):])
        if "range" in params:
            options={"period":params["range"]}
        elif params["period1"] < 0:
            options={"period":"max"}
        else:
            tz=ZoneInfo("Asia/Singapore" if symbol.endswith(".SI") else "America/New_York")
            day=datetime.fromtimestamp(params["period1"],timezone.utc).astimezone(tz).date().isoformat()
            options={"start":day}
        bars,_=self.source.history(symbol,**options)
        return Response(payload=chart_payload(bars,symbol))


class MobileYahooSmoke(YahooSmoke):
    title="Mobile Yahoo transport · synthetic HTTP test"

    def build(self):
        root=Path(temporary.name)
        self.client=FakeYahooClient()
        self.provider=create_provider(root,"android")
        self.cache=self.provider.cache
        self.provider.now=lambda:NOW
        self.provider._client=YahooJSONClient(root/"state",observer=self.cache.operation,
                                             session=RoutedSession(self.client),now=lambda:NOW)
        store=LineStore(root/"saved_lines.sqlite3")
        store.save("DEMO-SGX","Oscillating",20,12)
        self.screen=AnalyzerScreen(AnalyzerModel(store,self.provider))
        self.checks=[]
        return self.screen

    def steps(self):
        yield from super().steps()
        ui=self.screen
        calls=len(self.client.calls)
        ui.show_api_log()
        assert "Yahoo HTTPS" in ui.api_log_text.text
        assert "HTTP 200" in ui.api_log_text.text
        assert "cache_hit" in ui.api_log_text.text
        copy=next(w for w in ui.api_log_popup.content.children
                  if getattr(w,"text","")=="Copy diagnostic report")
        refresh=next(w for w in ui.api_log_popup.content.children
                     if getattr(w,"text","")=="Refresh log (no API call)")
        with patch("kivy.core.clipboard.Clipboard.copy") as clipboard:
            copy.dispatch("on_release")
            clipboard.assert_called_once()
            assert "SMA Stock Analyzer 0.8.0" in clipboard.call_args.args[0]
        refresh.dispatch("on_release")
        assert len(self.client.calls)==calls
        ui.api_log_popup.dismiss()
        self.checked("mobile HTTP statuses/cache hits copy to a report without new requests")

    def on_stop(self):
        self.screen.close()
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/mobile-yahoo-ui-smoke.json").write_text(json.dumps(
            {"passed":not self.failed,"checks":self.checks,
             "transport":"actual mobile JSON adapter; synthetic HTTP; not a physical phone"},indent=2))


if __name__ == "__main__":
    app=MobileYahooSmoke()
    app.run()
    temporary.cleanup()
    raise SystemExit(1 if app.failed else 0)
