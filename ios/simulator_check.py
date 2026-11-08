"""CI-only entry point; excluded from the downloadable device app."""
import json
import os
from pathlib import Path
import ssl
from zoneinfo import ZoneInfo

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Ellipse
from kivy.utils import platform

from sma_analyzer.app import AnalyzerScreen, DeviceFrame
from sma_analyzer.ios_runtime import IOSWindow, bridge, native_text
from sma_analyzer.market_data import PreviewMarketDataProvider
from sma_analyzer.model import AnalyzerModel
from sma_analyzer.storage import LineStore


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


class SimulatorCheck(App):
    def build(self):
        self.output = Path(self.user_data_dir) / "ios-smoke-result.json"
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.checks = []
        self.frames = 0
        self.adapter = IOSWindow()
        try:
            require(platform == "ios", "Kivy must select the iOS platform.")
            import requests
            import certifi
            require(Path(certifi.where()).is_file(), "Bundled TLS CA roots are missing.")
            require(ssl.OPENSSL_VERSION and requests.__version__, "TLS/HTTPS imports failed.")
            require(ZoneInfo("Asia/Singapore").key == "Asia/Singapore", "Timezone database missing.")
            self.checks.append("native iOS, HTTPS, CA roots and timezone imports")
            store = LineStore(Path(self.user_data_dir) / "qa-lines.sqlite3")
            existing = store.list_all_lines()
            if os.environ.get("SMA_IOS_CHECK_PHASE") == "2":
                require(any(line.custom_name == "iPhone persistence check" for line in existing), "Saved SMA lost across launches.")
                self.checks.append("SQLite saved name survives a second process launch")
            store.save("DEMO-SGX", "Sideways", 28, 12)
            saved = store.list_lines("DEMO-SGX", "Sideways")[0]
            store.rename(saved.id, "iPhone persistence check")
            self.ui = AnalyzerScreen(AnalyzerModel(store, PreviewMarketDataProvider()))
            self.frame = DeviceFrame(self.ui)
            self.adapter.start(self.frame.apply_metrics)
            Clock.schedule_interval(self.advance, 1/60)
            return self.frame
        except Exception as error:
            self.finish(False, str(error))
            raise

    def advance(self, _):
        try:
            self.frames += 1
            if self.frames == 15:
                metrics = json.loads(native_text(bridge().windowMetricsJSON()))
                require(metrics["width"] > 100 and metrics["height"] > 100, "UIKit window measurement failed.")
                self.checks.append("UIKit bridge and safe-area frame after layout")
                saved = self.ui.model.store.list_all_lines()[0]
                self.ui.on_view_saved(saved)
            if self.frames == 90:
                self.ui.show_color_picker()
            if self.frames < 150:
                return True
            require(len(self.ui.color_buttons) == 12, "Twelve palette options did not open.")
            for button in self.ui.color_buttons.values():
                swatch = next(item for item in button.canvas.before.children if isinstance(item, Ellipse))
                require(abs(swatch.pos[0]+swatch.size[0]/2 - button.x-button.width/2)<.5,
                        "Palette swatch is off-centre.")
                require(button.x+19 <= button.right, "Palette column too narrow.")
            require(not self.ui.busy, "The saved SMA did not load.")
            self.checks.append("shared library/chart/palette renders and stays centred in the iPhone event loop")
            self.finish(True, "")
            Clock.schedule_once(lambda _: self.stop(), .2)
        except Exception as error:
            self.finish(False, str(error))
            Clock.schedule_once(lambda _: self.stop(), .2)
        return False

    def finish(self, passed, error):
        value = {"passed":passed, "error":error, "checks":self.checks,
                 "launch_id":os.environ.get("SMA_IOS_CHECK_ID"), "platform":"iOS Simulator; controlled offline prices"}
        temporary = self.output.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, indent=2))
        temporary.replace(self.output)

    def on_stop(self):
        self.adapter.stop()
        bridge().stop()
        if hasattr(self, "ui"):
            self.ui.close()
