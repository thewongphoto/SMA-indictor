"""Exercise real Kivy widgets, worker completion, chart, and SQLite in a running app.

Run from the repository root: python -m scripts.smoke_ui
On headless Mesa/SDL Linux: SDL_VIDEODRIVER=offscreen LIBGL_ALWAYS_SOFTWARE=1 ...
Screenshots and a machine-readable current-run report go into artifacts/.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback

# Test storage never touches the user's saved lines.
temporary = tempfile.TemporaryDirectory(prefix="sma-ui-")
os.environ["SMA_ANALYZER_DATA_DIR"] = temporary.name

from sma_analyzer.app import SMAStockAnalyzerApp
from sma_analyzer.engine import crossover_events, simple_moving_average
from sma_analyzer.mock_data import Dataset
from kivy.clock import Clock
from kivy.core.window import Window


class SmokeApp(SMAStockAnalyzerApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.passed = []
        self.failure = None
        self.exit_code = 1
        self.steps = None

    def on_start(self):
        self.steps = self.exercise()
        Clock.schedule_once(self.advance, 0.2)

    def advance(self, _dt):
        try:
            next(self.steps)
            Clock.schedule_once(self.advance, 0.04)
        except StopIteration:
            self.exit_code = 0
            self.stop()
        except Exception:
            self.failure = traceback.format_exc()
            print(self.failure, file=sys.stderr)
            self.stop()

    def wait_for_calculation(self):
        deadline = time.monotonic() + 10
        while self.screen.busy:
            if time.monotonic() > deadline:
                raise AssertionError("UI calculation did not finish within 10 seconds")
            yield
        assert self.screen.model.result is not None, self.screen.status.text

    def check(self, name):
        self.passed.append(name)
        print(f"PASS: {name}", flush=True)

    def exercise(self):
        ui = self.screen
        assert len(ui.chart.prices) == 252 and not ui.chart.series
        assert ui.save_button.disabled
        self.check("initial unoptimized state")

        for target in [12, 6, 1]:
            ui.target.text = str(target)
            ui.optimize_button.dispatch("on_release")
            assert ui.busy and ui.optimize_button.disabled
            assert "Calculating" in ui.status.text
            yield from self.wait_for_calculation()
            result = ui.model.result
            assert result.target_frequency == target
            assert ui.card_values["target"].text == f"{target} / yr"
            assert ui.card_values["period"].text == f"{result.period} sessions"
            assert ui.card_values["actual"].text == f"{result.actual_annual_frequency:.2f} / yr"
            active, = [line for line in ui.chart.series if line.active]
            assert active.sma == tuple(simple_moving_average(ui.chart.prices, result.period))
            assert ui.chart.marker_events["active"] == result.events
            # Inspect the rendered table, not just the model's row list.
            rows = ui.model.event_rows()
            if rows:
                table = ui.table_panel.children[0]
                rendered = [cell.text for cell in reversed(table.children)]
                assert rendered[3:] == [value for row in rows for value in row]
            self.check(f"target {target}: button, loading, engine, cards, chart markers, table")

        for scenario in ["Trending", "Sideways", "Oscillating"]:
            previous = ui.chart.prices
            ui.scenario.text = scenario
            assert ui.chart.prices != previous and ui.model.result is None
            ui.optimize_button.dispatch("on_release")
            yield from self.wait_for_calculation()
            assert ui.chart.marker_events["active"] == crossover_events(
                ui.chart.prices, ui.model.result.sma)
        ui.counter.text = "DEMO-US"
        assert ui.chart.prices == ui.model.dataset.prices
        assert "DEMO-US" in ui.plot_title.text
        self.check("all scenario selectors and both fictional counters refresh prices")

        ui.target.text = "Custom"
        ui.custom_target.text = "9"
        ui.optimize_button.dispatch("on_release")
        yield from self.wait_for_calculation()
        assert ui.card_values["target"].text == "9 / yr"
        ui.custom_target.text = "invalid"
        ui.optimize_button.dispatch("on_release")
        assert not ui.busy and "positive whole number" in ui.status.text
        assert ui.model.result is None and ui.save_button.disabled
        self.check("custom frequency and helpful invalid-input state")

        ui.target.text = "12"
        ui.optimize_button.dispatch("on_release")
        yield from self.wait_for_calculation()
        ui.save_button.dispatch("on_release")
        assert len(ui.model.saved_lines()) == 1
        ui.hide_button.dispatch("on_release")
        assert not ui.chart.series
        ui.hide_button.dispatch("on_release")
        assert len(ui.chart.series) == 1
        saved = ui.model.saved_lines()[0]
        ui.on_saved_visibility(saved)
        assert not ui.chart.series and not ui.model.saved_lines()[0].visible
        ui.on_saved_visibility(ui.model.saved_lines()[0])
        assert len(ui.chart.series) == 1
        ui.target.text = "6"
        ui.optimize_button.dispatch("on_release")
        yield from self.wait_for_calculation()
        ui.save_button.dispatch("on_release")
        assert len(ui.model.saved_lines()) == 2
        self.check("save, multiple overlays, hide/show, persistent saved-line toggles")

        for size in [(320, 640), (440, 920), (560, 1000)]:
            Window.size = size
            for _ in range(4):
                yield
            assert ui.content.width <= size[0]
            assert ui.chart.width > 200
            assert ui.chart.height >= 240
        Window.size = (440, 920)
        ui.scroll.scroll_y = 1
        for _ in range(6):
            yield
        Path("artifacts").mkdir(exist_ok=True)
        ui.export_to_png("artifacts/prototype-phone.png")
        ui.content.export_to_png("artifacts/prototype-full.png")
        self.check("three portrait sizes render and screenshots export")

        ui.on_delete(ui.model.saved_lines()[0])
        assert len(ui.model.saved_lines()) == 1
        ui.model.dataset = Dataset("DEMO-US", "Oscillating", ())
        ui.model.result = None
        ui.refresh()
        assert ui.chart.prices == () and ui.chart.marker_events == {}
        ui.optimize_button.dispatch("on_release")
        deadline = time.monotonic() + 10
        while ui.busy:
            assert time.monotonic() < deadline
            yield
        assert "At least 3 sessions" in ui.status.text
        assert ui.model.result is None
        self.check("remove line, empty chart, insufficient-data error without crash")


if __name__ == "__main__":
    app = SmokeApp()
    started = time.time()
    try:
        app.run()
    finally:
        Path("artifacts").mkdir(exist_ok=True)
        report = {"started_unix": started, "passed": app.passed,
                  "passed_count": len(app.passed), "failure": app.failure,
                  "exit_code": app.exit_code}
        Path("artifacts/ui-smoke.json").write_text(json.dumps(report, indent=2) + "\n")
        temporary.cleanup()
    raise SystemExit(app.exit_code)
