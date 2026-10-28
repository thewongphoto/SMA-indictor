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
from kivy.base import EventLoop
from kivy.graphics import Color, Line, Rectangle, Triangle
from kivy.input.motionevent import MotionEvent
from kivy.metrics import dp

from sma_analyzer.chart import START_COLOR, END_COLOR


class Pointer(MotionEvent):
    """Synthetic finger sent through the real window/scroll/touch-grab pipeline."""
    def __init__(self, x, y):
        super().__init__("smoke", id(self), self.coordinates(x, y), is_touch=True, type_id="touch")
        self.profile = ["pos"]

    @staticmethod
    def coordinates(x, y):
        return {"x": x / (Window.width - 1), "y": y / (Window.height - 1)}

    def depack(self, args):
        self.sx, self.sy = args["x"], args["y"]
        super().depack(args)

    def down(self):
        EventLoop.post_dispatch_input("begin", self)

    def move_to(self, x, y, dispatch=True):
        self.move(self.coordinates(x, y))
        if dispatch:
            EventLoop.post_dispatch_input("update", self)

    def up(self):
        EventLoop.post_dispatch_input("end", self)


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
        # Font textures and minimum-height bindings settle over multiple frames.
        # Wait for actual layout instead of relying on a fixed startup delay.
        deadline = time.monotonic() + 3
        while ui.optimal_panel.top <= ui.chart.parent.top:
            assert time.monotonic() < deadline, "Optimal SMA panel must be above the chart"
            yield
        assert len(ui.chart.prices) == 1260 and not ui.chart.series
        assert ui.chart.viewport.bounds == (1008, 1259)
        assert ui.timeline_selector.text == "1Y"
        assert tuple(ui.timeline_selector.values) == ("1Y", "3Y", "5Y", "Max")
        assert "count" not in ui.card_values
        assert len(ui.cards.children) == 2
        assert ui.save_button.parent.parent is ui.optimal_panel
        assert ui.hide_button.parent.parent is ui.optimal_panel
        assert ui.optimal_panel.top > ui.chart.parent.top
        assert ui.save_button.disabled
        self.check("initial unoptimized state")

        for target in [12, 6, 1]:
            ui.target.text = str(target)
            ui.optimize_button.dispatch("on_release")
            assert ui.busy and ui.optimize_button.disabled
            assert "Calculating" in ui.status.text
            yield from self.wait_for_calculation()
            result = ui.model.result
            assert "outlined plus signs" in ui.status.text
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

        result_before = ui.model.result
        summary_before = ui.model.summary()
        for label, bounds in [("3Y",(504,1259)), ("5Y",(0,1259)), ("Max",(0,1259)), ("1Y",(1008,1259))]:
            ui.timeline_selector._dropdown.select(label)
            assert ui.chart.viewport.bounds == bounds
            assert ui.model.result is result_before
            assert ui.model.summary() == summary_before
            assert not ui.chart.is_zoomed
        assert ui.legend_labels[:2] == ["simulated close", "upward crossings"]
        assert all(":" not in label and "Triangles" not in label for label in ui.legend_labels)
        self.check("timeline ranges preserve full-history results; revised cards, contained actions and symbol legend")
        original_data = ui.model.dataset
        for length, choices in [(500,("1Y","Max")), (756,("1Y","3Y","Max")), (1259,("1Y","3Y","Max"))]:
            ui.model.dataset = Dataset(original_data.counter, original_data.scenario, original_data.prices[:length])
            ui.model.result = None
            ui.refresh()
            assert tuple(ui.timeline_selector.values) == choices
            assert ui.timeline_selector.text == "1Y"
        ui.model.select_dataset(original_data.counter, original_data.scenario)
        ui.refresh()
        self.check("short-history dropdown omits unavailable 3Y and 5Y choices; dataset change defaults to 1Y")

        for scenario in ["Trending", "Sideways", "Oscillating"]:
            previous = ui.chart.prices
            ui.scenario.text = scenario
            assert ui.chart.prices != previous and ui.model.result is None
            ui.optimize_button.dispatch("on_release")
            yield from self.wait_for_calculation()
            assert ui.chart.marker_events["active"] == crossover_events(
                ui.chart.prices, ui.model.result.sma)
        ui.scenario.text = "Sideways"
        ui.target.text = "12"
        ui.optimize_button.dispatch("on_release")
        yield from self.wait_for_calculation()
        assert ui.card_values["period"].text == "254 sessions"
        assert ui.card_values["actual"].text == "31.31 / yr"
        assert "125 upward crossings" in ui.crossing_count_label.text
        assert "1006 usable comparisons" in ui.explanation.text
        assert "SMA search: 2–756" in ui.explanation.text
        assert "Warm-up is included" not in ui.explanation.text
        assert "not matched exactly" in ui.explanation.text
        self.check("active adjusted-frequency policy: known sideways result, coverage, cap, unreachable target")
        ui.scenario.text = "Oscillating"
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

        # Measure the completed analysis layout, after save feedback has cleared.
        ui.optimize_button.dispatch("on_release")
        yield from self.wait_for_calculation()
        assert ui.status.parent is None
        for size in [(320, 640), (440, 920), (560, 1000), (760, 1100), (960, 1440)]:
            Window.size = size
            for _ in range(4):
                yield
            assert ui.content.width <= size[0]
            assert ui.chart.width > 200
            assert ui.chart.height >= 240
            wide = size[0] >= 760
            assert ui.control_grid.cols == (4 if wide else 2)
            if wide:
                assert abs(ui.counter.y - ui.scenario.y) < dp(1)
                assert abs(ui.counter.y - ui.target.y) < dp(1)
                assert abs(ui.counter.y - ui.optimize_button.y) < dp(1)
                assert ui.counter.right < ui.scenario.x
                assert ui.scenario.right < ui.target.x
                assert ui.target.right < ui.optimize_button.x
                assert ui.controls.height < dp(130), "Completed controls must remain compact"
                assert ui.optimal_panel.orientation == "horizontal"
                assert ui.card_values["period"].right <= ui.save_button.x
            else:
                assert abs(ui.counter.y - ui.scenario.y) < dp(1)
                assert ui.counter.y > ui.target.y
                assert ui.controls.height < dp(185)
            for widget in [ui.counter, ui.scenario, ui.target, ui.optimize_button,
                           ui.save_button, ui.hide_button]:
                assert widget.width >= dp(110)
                assert widget.x >= ui.content.x and widget.right <= ui.content.right
                assert widget.height >= dp(44)
            if size[0] == 320:
                ui.export_to_png("artifacts/prototype-small-phone.png")
        Window.size = (440, 920)
        ui.scroll.scroll_y = 1
        for _ in range(6):
            yield
        Path("artifacts").mkdir(exist_ok=True)
        ui.export_to_png("artifacts/prototype-phone.png")
        ui.content.export_to_png("artifacts/prototype-full.png")
        self.check("five portrait sizes: compact aligned controls, responsive Optimal card, touch targets and screenshots")

        # Hit the arrow in each top selector through normal window routing.
        for selector, option in [(ui.counter,"DEMO-SGX"), (ui.scenario,"Trending"), (ui.target,"12 / year")]:
            ui.scroll.scroll_y = 1
            for _ in range(6):
                yield
            pointer = Pointer(*selector.to_window(selector.right-dp(8), selector.center_y))
            pointer.down()
            pointer.up()
            for _ in range(14):
                yield
            assert selector.is_open, "Entire rounded control including chevron must open dropdown"
            selector._dropdown.select(option)
            for _ in range(4):
                yield
        ui.optimize_button.dispatch("on_release")
        yield from self.wait_for_calculation()
        assert ui.model.result.target_frequency == 12
        assert ui.model.result.period == 11
        assert ui.status.parent is None, "Completed state must not inflate the control panel"
        Window.size = (960, 1440)
        ui.scroll.scroll_y = 1
        for _ in range(8):
            yield
        ui.export_to_png("artifacts/prototype-wide.png")
        ui.content.export_to_png("artifacts/prototype-wide-full.png")
        Window.size = (440, 920)
        for _ in range(8):
            yield
        ui.export_to_png("artifacts/prototype-phone.png")
        ui.content.export_to_png("artifacts/prototype-full.png")
        # Restore the dataset/result expected by the original range-zoom checks.
        ui.counter.text = "DEMO-US"
        ui.scenario.text = "Oscillating"
        ui.target.text = "6"
        ui.optimize_button.dispatch("on_release")
        yield from self.wait_for_calculation()
        self.check("all top dropdown arrows respond to real clicks; annual target labels parse; mockup screenshots captured")

        # Scroll first so the real event pipeline must transform coordinates.
        ui.scroll.scroll_to(ui.chart, animate=False)
        for _ in range(6):
            yield
        chart = ui.chart

        arrow = Pointer(*ui.timeline_selector.to_window(ui.timeline_selector.right-dp(8), ui.timeline_selector.center_y))
        arrow.down()
        arrow.up()
        for _ in range(14):
            yield
        assert ui.timeline_selector.is_open, "Arrow area must open the same dropdown as the label"
        options = {option.text: option for option in ui.timeline_selector._dropdown.container.children}
        assert set(options) == {"1Y","3Y","5Y","Max"}
        assert options["1Y"].background_color != options["3Y"].background_color
        options["3Y"].dispatch("on_release")
        assert chart.viewport.bounds == (504,1259)
        # Re-select the same preset after a custom zoom to restore its baseline.
        chart.viewport.select(600,700)
        chart._sync_view()
        options["3Y"].dispatch("on_release")
        assert chart.viewport.bounds == (504,1259) and not chart.is_zoomed
        options["1Y"].dispatch("on_release")
        for _ in range(6):
            yield
        self.check("rounded dropdown arrow is clickable; selected option shaded; selecting same preset resets drag zoom")

        def location(fraction, y_fraction=0.5):
            left, bottom, width, height = chart.plot_rect
            return chart.to_window(left + fraction * width, bottom + y_fraction * height)

        def assert_guides():
            colors = [instruction.rgba for instruction in chart.canvas.children
                      if isinstance(instruction, Color)]
            for actual, expected in zip(colors[-2:], (START_COLOR, END_COLOR)):
                assert all(abs(a - b) < 1e-6 for a, b in zip(actual, expected))
            guides = [instruction for instruction in chart.canvas.children if isinstance(instruction, Line)][-2:]
            assert guides[0].points[0] < guides[1].points[0]
            shade = [instruction for instruction in chart.canvas.children if isinstance(instruction, Rectangle)][-1]
            assert shade.size[0] > 0

        assert not chart.is_zoomed and ui.zoom_out_button.parent is None
        full_sma = ui.model.result.sma
        full_events = ui.model.result.events
        full_summary = ui.model.summary()
        full_limits = chart.viewport.y_limits(chart.prices, [line.sma for line in chart.series])
        scroll_position = ui.scroll.scroll_y
        finger = Pointer(*location(0.25))
        finger.down()
        assert chart.selection is not None, "Plot selection must start immediately, without scroll timeout"
        assert chart.selection.anchor == chart.selection.cursor
        finger.move_to(*location(0.75, 0.6))
        assert chart.selection.cursor > chart.selection.anchor
        assert_guides()
        assert ui.scroll.scroll_y == scroll_position
        # Crossing the original touch position reverses which boundary moves.
        finger.move_to(*location(0.1))
        assert chart.selection.cursor < chart.selection.anchor
        assert_guides()
        chart.parent.export_to_png("artifacts/zoom-select-left.png")
        finger.move_to(*location(0.75))
        assert_guides()
        chart.parent.export_to_png("artifacts/zoom-select-right.png")
        second = Pointer(*location(0.5))
        second.down()
        assert chart._drag_touch is finger
        second.up()
        finger.up()
        assert chart.selection is None and chart._drag_touch is None
        assert chart.viewport.bounds == (1070, 1197), chart.viewport.bounds
        assert chart.is_zoomed and ui.zoom_out_button.parent is ui.plot_header
        zoom_limits = chart.viewport.y_limits(chart.prices, [line.sma for line in chart.series])
        assert zoom_limits != full_limits
        assert ui.model.result.sma is full_sma and ui.model.result.events is full_events
        assert ui.model.summary() == full_summary
        assert "sessions 1071–1198" in ui.plot_subtitle.text
        outlines = [item for item in chart.canvas.children if isinstance(item, Line) and item.close and len(item.points) == 24]
        assert not any(isinstance(item, Triangle) for item in chart.canvas.children)
        expected_markers = sum(1070 <= event.index <= 1197
                               for events in chart.marker_events.values() for event in events)
        assert len(outlines) == expected_markers
        for _ in range(4):
            yield
        chart.parent.export_to_png("artifacts/zoom-active.png")
        self.check("real touch routing, immediate guides, both colors, shading, crossing anchor, y rescale, unchanged calculations")

        Window.size = (320, 640)
        for _ in range(6):
            yield
        assert chart.viewport.bounds == (1070, 1197)
        assert ui.zoom_out_button.right <= chart.parent.right
        chart.parent.export_to_png("artifacts/zoom-phone-320.png")
        Window.size = (440, 920)
        for _ in range(6):
            yield
        ui.scroll.scroll_to(chart, animate=False)
        for _ in range(4):
            yield

        finger = Pointer(*location(0.8))
        finger.profile.append("button")
        finger.button = "left"
        finger.down()
        # Release coordinates also work without a provider sending a final move.
        finger.move_to(*location(0.2), dispatch=False)
        finger.up()
        assert chart.viewport.bounds == (1095, 1172), chart.viewport.bounds
        ui.hide_button.dispatch("on_release")
        assert chart.viewport.bounds == (1095, 1172)
        ui.hide_button.dispatch("on_release")
        # Use actual window touches for the top-right button, not its callback.
        for _ in range(4):
            yield
        button = Pointer(*ui.zoom_out_button.to_window(*ui.zoom_out_button.center))
        button.down()
        button.up()
        for _ in range(12):
            yield
        assert chart.viewport.bounds == (1008, 1259)
        assert not chart.is_zoomed and ui.zoom_out_button.parent is None
        self.check("leftward nested zoom, overlays preserve view, zoom-out button restores selected timeline and disappears")

        for movement in [0, dp(2)]:
            finger = Pointer(*location(0.4))
            finger.down()
            x, y = location(0.4)
            finger.move_to(x + movement, y)
            finger.up()
            assert not chart.is_zoomed
        finger = Pointer(*location(0.5))
        finger.down()
        finger.move_to(*location(1.3, 1.2))
        finger.up()
        assert chart.viewport.bounds == (1133, 1259)
        ui.scenario.text = "Trending"
        assert chart.viewport.bounds == (1008, 1259) and not chart.is_zoomed
        assert ui.zoom_out_button.parent is None
        self.check("taps/jitter ignored, outside-plot release clamped, new scenario resets zoom")

        # Page scrolling is still available when the gesture starts outside the plot.
        before = ui.scroll.scroll_y
        x = ui.scroll.x + dp(5)
        finger = Pointer(x, ui.scroll.center_y)
        finger.down()
        for _ in range(3):
            yield
        finger.move_to(x, ui.scroll.center_y + dp(70))
        for _ in range(3):
            yield
        finger.up()
        for _ in range(3):
            yield
        assert ui.scroll.scroll_y != before
        self.check("page scroll still works outside the plot")

        ui.scenario.text = "Oscillating"
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
        assert "At least 4 sessions" in ui.status.text
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
