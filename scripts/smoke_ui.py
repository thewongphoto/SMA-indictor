"""Exercise real Kivy widgets, worker completion, chart, and SQLite in a running app.

Run from the repository root: python -m scripts.smoke_ui
On headless Mesa/SDL Linux: SDL_VIDEODRIVER=offscreen LIBGL_ALWAYS_SOFTWARE=1 ...
Screenshots and a machine-readable current-run report go into artifacts/.
"""
import json
import io
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback

# Test storage never touches the user's saved lines.
temporary = tempfile.TemporaryDirectory(prefix="sma-ui-")
os.environ["SMA_ANALYZER_DATA_DIR"] = temporary.name

from sma_analyzer.app import SMAStockAnalyzerApp, AnalyzerScreen
from sma_analyzer.android_window import WindowMetrics
from sma_analyzer.model import AnalyzerModel
from sma_analyzer.storage import LineStore
from sma_analyzer.engine import crossover_events, simple_moving_average
from sma_analyzer.mock_data import Dataset
from unittest.mock import Mock, patch
from sma_analyzer.notifications import evaluate_eod
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
        if "--android-regressions-only" in sys.argv:
            # Keep a 440×920 dp viewport when exercising phone pixel densities.
            Window.size=(int(dp(440)),int(dp(920)))
            for _ in range(8): yield
            yield from self.android_regressions()
            return
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
        assert not ui.save_button.selected and ui.save_button.text == ""
        assert ui.manager.current == "parameters"
        assert ui.controls.parent is ui.parameter_content
        assert ui.optimal_panel.parent is ui.content
        assert not ui.saved_sheet.is_open
        for _ in range(4): yield
        ui.export_to_png("artifacts/screen-1-parameters.png")
        self.check("initial parameters screen; result, settings and saved-sheet separation")

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
                table = ui.crossover_table
                rendered = [cell.text for cell in reversed(table.children)]
                assert rendered[3:] == [value for row in rows[:5] for value in row]
            assert ui.manager.current == "results"
            assert len(ui.rendered_crossover_rows) == min(5,len(rows))
            self.check(f"target {target}: button, loading, engine, cards, chart markers, table")

        # A short history of events stops at its actual count, with no Show all.
        assert len(ui.model.event_rows()) == 26
        for expected in (15,25,26):
            assert ui.more_crossings_button.kind == "down"
            ui.more_crossings_button.dispatch("on_release")
            assert len(ui.rendered_crossover_rows) == expected
        assert ui.more_crossings_button is None
        ui.hide_button.dispatch("on_release")
        assert len(ui.rendered_crossover_rows) == 26
        ui.hide_button.dispatch("on_release")
        old_result = ui.model.result
        ui.scroll.scroll_to(ui.optimal_panel,animate=False)
        for _ in range(6): yield
        pointer = Pointer(*ui.change_parameters_button.to_window(*ui.change_parameters_button.center))
        pointer.down(); pointer.up()
        for _ in range(8): yield
        assert ui.manager.current == "parameters"
        assert ui.model.result is old_result
        assert ui.target.text == "1" and ui.counter.text == "DEMO-SGX"
        assert ui.scenario.text == "Oscillating"
        # Normal successful calculation returns to Results with a fresh five rows.
        ui.optimize_button.dispatch("on_release")
        yield from self.wait_for_calculation()
        assert ui.manager.current == "results" and len(ui.rendered_crossover_rows)==5
        self.check("short crossover list ends cleanly; Change parameters preserves form and reoptimization resets five rows")

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
        # Five rows initially; arrows reveal ten more, then Show all after 35.
        original_result = ui.model.result
        for expected in (15,25,35):
            assert ui.more_crossings_button.kind == "down"
            ui.more_crossings_button.dispatch("on_release")
            assert len(ui.rendered_crossover_rows) == expected
            assert ui.rendered_crossover_rows == ui.model.event_rows()[:expected]
        assert ui.more_crossings_button.text == "Show all"
        ui.scroll.scroll_y = .35
        original_offset = ui.scroll.scroll_y
        ui.more_crossings_button.dispatch("on_release")
        assert ui.manager.current == "crossovers"
        cells = [cell.text for cell in reversed(ui.full_crossover_table.children)]
        assert cells[3:] == [value for row in ui.model.event_rows() for value in row]
        assert len(ui.model.event_rows()) == 125
        for _ in range(6): yield
        ui.export_to_png("artifacts/screen-2a-expanded.png")
        ui.full_crossovers_scroll.scroll_y = 0
        for _ in range(6): yield
        # Back stays fixed at the top even after scrolling all 125 events.
        assert ui.crossovers_back_button.to_window(*ui.crossovers_back_button.center)[1] > ui.height-dp(60)
        pointer = Pointer(*ui.crossovers_back_button.to_window(*ui.crossovers_back_button.center))
        pointer.down(); pointer.up()
        for _ in range(6): yield
        assert ui.manager.current == "results" and ui.model.result is original_result
        assert ui.scroll.scroll_y == original_offset
        assert len(ui.rendered_crossover_rows) == 35
        self.check("crossovers 5/15/25/35, Show all exact events and full-screen back preserves state")

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
        assert ui.save_button.selected
        assert ui.saved_sheet.is_open
        assert ui.saved_menu_button.kind == "down"
        for _ in range(8): yield
        assert ui.saved_sheet.body.top < ui.height
        assert ui.saved_sheet.body.y >= ui.results_footer.top-dp(1)
        original_bounds = ui.chart.viewport.bounds
        # The persistent bottom-left menu toggles the sheet down, then up.
        pointer = Pointer(*ui.saved_menu_button.to_window(*ui.saved_menu_button.center))
        pointer.down(); pointer.up()
        for _ in range(10): yield
        assert not ui.saved_sheet.is_open and ui.saved_sheet.parent is None
        assert ui.saved_menu_button.kind == "menu"
        pointer = Pointer(*ui.saved_menu_button.to_window(*ui.saved_menu_button.center))
        pointer.down(); pointer.up()
        for _ in range(10): yield
        assert ui.saved_sheet.is_open
        ui.export_to_png("artifacts/screen-2b-saved-sheet.png")
        grip = ui.saved_sheet.handle
        pointer = Pointer(*grip.to_window(*grip.center))
        pointer.down()
        pointer.move_to(pointer.x,pointer.y-dp(100))
        pointer.up()
        for _ in range(10): yield
        assert not ui.saved_sheet.is_open and ui.saved_sheet.parent is None
        assert ui.chart.viewport.bounds == original_bounds
        # Settings and back are real native buttons, not callback-only tests.
        result = ui.model.result
        pointer = Pointer(*ui.settings_button.to_window(*ui.settings_button.center))
        pointer.down(); pointer.up()
        for _ in range(6): yield
        assert ui.manager.current == "settings"
        pointer = Pointer(*ui.settings_back_button.to_window(*ui.settings_back_button.center))
        pointer.down(); pointer.up()
        for _ in range(6): yield
        assert ui.manager.current == "results" and ui.model.result is result
        assert ui.chart.viewport.bounds == original_bounds
        self.check("save opens partial sheet; menu toggle and swipe dismiss; settings/back retain analysis")

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

        saved = ui.model.current_saved_line()
        row = ui.saved_rows[saved.id]
        row["email"].dispatch("on_release")
        for _ in range(4): yield
        assert ui.validation_popup._is_open
        assert "email address" in ui.notification_status.text
        assert not ui.model.current_saved_line().email_enabled
        ui.validation_popup.dismiss()
        ui.show_settings()
        ui.email_input.text = "bad-address"
        ui.email_save_button.dispatch("on_release")
        assert "valid email" in ui.notification_status.text
        ui.email_input.text = "reader@example.com"
        ui.email_save_button.dispatch("on_release")
        assert ui.model.store.notification_settings().email == "reader@example.com"
        for switch in ui.notification_switches.values():
            switch.active = True
        switch = ui.notification_switches["phone_buy"]
        ui.settings_scroll.scroll_to(switch,animate=False)
        for _ in range(6): yield
        for expected in (False,True):
            pointer = Pointer(*switch.to_window(*switch.center))
            pointer.down()
            pointer.up()
            for _ in range(14): yield
            assert switch.active == expected
            assert ui.model.store.notification_settings().phone_buy == expected
        ui.saved_rows[saved.id]["email"].dispatch("on_release")
        ui.saved_rows[saved.id]["push"].dispatch("on_release")
        assert ui.model.current_saved_line().email_enabled
        assert ui.model.current_saved_line().push_enabled
        assert ui.saved_rows[saved.id]["email"].text.endswith("On")
        assert ui.saved_rows[saved.id]["push"].text.endswith("On")
        self.check("email validation popup, saved address, four persistent type switches, independent saved-line channels")

        session = ui.model.result.events[-1].index + 1
        ui.alert_session.text = str(session)
        ui.preview_alert_button.dispatch("on_release")
        assert len(ui.last_alerts) == 2
        assert "Buy Signal for DEMO-US" in ui.alert_preview.text
        assert "SIMULATED DATA" in ui.alert_preview.text
        assert all(not ui.model.store.was_delivered(a.key) for a in ui.last_alerts)
        phone = Mock()
        with patch("sma_analyzer.notifications.AndroidNotifier",return_value=phone) as notifier:
            notifier.request_permission.side_effect = lambda callback=None: callback(True) if callback else None
            ui.eod_deliver_button.dispatch("on_release")
            deadline = time.monotonic()+5
            while ui.eod_deliver_button.disabled:
                assert time.monotonic()<deadline
                yield
            assert phone.send.call_count == 1
            assert "Email not sent" in ui.notification_status.text
            ui.eod_deliver_button.dispatch("on_release")
            while ui.eod_deliver_button.disabled:
                assert time.monotonic()<deadline
                yield
            assert phone.send.call_count == 1
        below = next(i+1 for i,(price,sma) in enumerate(zip(ui.chart.prices,ui.model.result.sma))
                     if sma is not None and price < sma)
        ui.alert_session.text = str(below)
        ui.preview_alert_button.dispatch("on_release")
        assert all(a.kind == "monitor" for a in ui.last_alerts) and len(ui.last_alerts)==2
        assert "Impending buy signal for DEMO-US" in ui.alert_preview.text
        ui.phone_test_button.dispatch("on_release")
        assert "Android development build" in ui.notification_status.text
        ui.alert_session.text = "0"
        ui.preview_alert_button.dispatch("on_release")
        assert "between 1 and" in ui.alert_preview.text
        self.check("real EOD preview buttons, buy/monitor contents, mocked Android delivery, duplicate suppression, desktop limitation")

        # Exercise actual Gmail UI controls with fake Google consent and HTTP;
        # no real Google token, account access or email is used by this runner.
        original_authorizer = ui.gmail_authorizer
        original_transport = ui.gmail_sender._transport
        authorizer = Mock()
        authorizer.authorize.side_effect = lambda sender, ok, failed: ok("test-token")
        authorizer.revoke.side_effect = lambda sender, done, failed: done()
        ui.gmail_authorizer = authorizer
        transport = Mock(side_effect=lambda *a,**k: io.BytesIO(b'{"id":"ui-test-email"}'))
        ui.gmail_sender._transport = transport
        ui.gmail_connect_button.dispatch("on_release")
        deadline = time.monotonic()+5
        while ui.delivery_busy:
            assert time.monotonic()<deadline
            yield
        assert ui.gmail_sender.connected and "Connected" in ui.gmail_status.text
        ui.gmail_test_button.dispatch("on_release")
        while ui.delivery_busy:
            assert time.monotonic()<deadline
            yield
        assert "Test email accepted" in ui.notification_status.text
        assert transport.call_count==1
        ui.preview_alert_button.dispatch("on_release")
        assert transport.call_count==1, "Preview must never send Gmail messages"
        ui.gmail_disconnect_button.dispatch("on_release")
        while ui.delivery_busy:
            assert time.monotonic()<deadline
            yield
        assert not ui.gmail_sender.connected and "Disconnected" in ui.gmail_status.text
        ui.gmail_authorizer = original_authorizer
        ui.gmail_sender._transport = original_transport
        ui.gmail_connect_button.dispatch("on_release")
        assert not ui.delivery_busy and "Android build" in ui.gmail_status.text
        self.check("Gmail connect, explicit test send, preview isolation and disconnect with fake OAuth/HTTP")

        ui.show_results()
        ui.scroll.scroll_to(ui.optimal_panel,animate=False)
        for _ in range(6): yield
        pointer = Pointer(*ui.save_button.to_window(*ui.save_button.center))
        pointer.down()
        pointer.up()
        for _ in range(6): yield
        assert not ui.save_button.selected and len(ui.model.saved_lines()) == 1
        history = ui.model.store.recent_unsaved()[0]
        assert history.target_frequency == 6
        ui.saved_sheet.open()
        for _ in range(8): yield
        ui.saved_sheet.scroll.scroll_to(ui.saved_panel,animate=False)
        for _ in range(6): yield
        pointer = Pointer(*ui.history_button.to_window(*ui.history_button.center))
        pointer.down()
        pointer.up()
        for _ in range(4): yield
        assert ui.history_popup._is_open and len(ui.history_restore_buttons)==1
        ui.history_popup.export_to_png("artifacts/recent-unsaved.png")
        ui.history_restore_buttons[history.id].dispatch("on_release")
        assert ui.save_button.selected and len(ui.model.saved_lines())==2
        assert not ui.model.store.recent_unsaved()
        assert ui.model.current_saved_line().email_enabled
        self.check("outline/red heart toggles, history popup and restore preserve saved notification flags")

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
            ui.show_parameters()
            for _ in range(4): yield
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
            for widget in [ui.counter, ui.scenario, ui.target, ui.optimize_button]:
                assert widget.width >= dp(110)
                assert widget.x >= ui.content.x and widget.right <= ui.content.right
                assert widget.height >= dp(44)
            ui.show_results()
            for _ in range(4): yield
            assert ui.hide_button.width == dp(88)
            assert ui.change_parameters_button.width >= dp(110)
            assert ui.saved_menu_button.height >= dp(44)
            assert ui.settings_button.right <= ui.width
            assert ui.save_button.width == dp(44) and ui.save_button.height >= dp(44)
            ui.saved_sheet.open()
            for _ in range(8): yield
            for line in ui.model.saved_lines():
                row = ui.saved_rows[line.id]
                for key in ("push","email"):
                    assert row[key].width >= row[key].texture_size[0], "Saved notification label must fit"
                assert row["hide"].right <= row["heart"].x
                assert abs(row["heart"].right - (ui.saved_panel.right-dp(14))) < dp(1)
                active = ui.model.result is not None and line.period == ui.model.result.period
                assert row["swatch"].ink == ui.chart.period_color(line.period,active)
            ui.saved_sheet.dismiss(animate=False)
            if size[0] == 320:
                ui.export_to_png("artifacts/prototype-small-phone.png")
        Window.size = (440, 920)
        ui.scroll.scroll_y = 1
        for _ in range(6):
            yield
        Path("artifacts").mkdir(exist_ok=True)
        ui.export_to_png("artifacts/prototype-phone.png")
        ui.content.export_to_png("artifacts/prototype-full.png")
        ui.alert_session.text = str(ui.model.result.events[-1].index+1)
        ui.preview_alert_button.dispatch("on_release")
        for _ in range(4): yield
        ui.saved_panel.export_to_png("artifacts/saved-lines-phone.png")
        ui.settings_panel.export_to_png("artifacts/notification-settings.png")
        self.check("five portrait sizes: compact aligned controls, responsive Optimal card, touch targets and screenshots")

        # Hit the arrow in each top selector through normal window routing.
        ui.show_parameters()
        for selector, option in [(ui.counter,"DEMO-SGX"), (ui.scenario,"Trending"), (ui.target,"12 / year")]:
            ui.parameter_scroll.scroll_y = 1
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
        # Start away from either scroll boundary; settings make the page longer.
        ui.scroll.scroll_y = 0.5
        for _ in range(6): yield
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

        # Real optimizer results for the requested example: SGX Trending chooses
        # SMA 11 for target 12 and SMA 18 for target 1. Capture both saved rows.
        ui.counter.text = "DEMO-SGX"
        ui.scenario.text = "Trending"
        for target, expected in ((12,11),(1,18),(12,11)):
            ui.target.text = str(target)
            ui.optimize_button.dispatch("on_release")
            yield from self.wait_for_calculation()
            assert ui.model.result.period == expected
            if ui.model.current_saved_line() is None:
                ui.save_button.dispatch("on_release")
        line = ui.model.current_saved_line()
        ui.model.store.set_notifications(line.id,"phone",True)
        ui.model.store.set_notifications(line.id,"email",True)
        ui.refresh()
        ui.alert_session.text = str(ui.model.result.events[-1].index+1)
        ui.preview_alert_button.dispatch("on_release")
        assert len(ui.last_alerts)==2
        assert {p.period for p in ui.chart.series} == {11,18}
        for plotted in ui.chart.series:
            saved = next(s for s in ui.model.saved_lines() if s.period == plotted.period)
            assert ui.saved_rows[saved.id]["swatch"].ink == ui.chart.line_color(plotted,0)
        for _ in range(8): yield
        ui.saved_panel.export_to_png("artifacts/saved-lines-phone.png")
        ui.settings_panel.export_to_png("artifacts/notification-settings.png")
        ui.saved_sheet.dismiss(animate=False)
        ui.scroll.scroll_y = 1
        for _ in range(6): yield
        ui.export_to_png("artifacts/prototype-phone.png")
        ui.content.export_to_png("artifacts/screen-2-results-full.png")
        ui.show_parameters()
        for _ in range(6): yield
        ui.export_to_png("artifacts/screen-1-parameters.png")
        ui.show_settings()
        ui.settings_scroll.scroll_y = 1
        for _ in range(6): yield
        ui.export_to_png("artifacts/screen-3-settings.png")
        ui.show_results()
        ui.saved_sheet.open()
        for _ in range(10): yield
        ui.export_to_png("artifacts/screen-2b-saved-sheet.png")
        ui.saved_sheet.dismiss(animate=False)
        Window.size = (960,1440)
        for _ in range(8): yield
        ui.saved_panel.export_to_png("artifacts/saved-lines-wide.png")
        ui.export_to_png("artifacts/prototype-wide.png")
        self.check("SMA 11 and 18 real results: distinct chart-matched swatches, hearts, channels and final screenshots")
        yield from self.android_regressions()

    def android_regressions(self):
        ui = self.screen
        if ui.model.result is None or ui.model.result.crossing_count<=35:
            ui.counter.text="DEMO-SGX"
            ui.scenario.text="Trending"
            ui.target.text="12"
            ui.on_optimize()
            yield from self.wait_for_calculation()
            ui.model.save_current()
            ui.refresh()
        for _ in range(8): yield

        # Android regression: the text beside the menu icon is also a hit target.
        ui.show_results()
        pointer = Pointer(*ui.saved_menu_label.to_window(*ui.saved_menu_label.center))
        pointer.down(); pointer.up()
        for _ in range(10): yield
        assert ui.saved_sheet.is_open and ui.saved_sheet.body.height > 0
        assert ui.saved_sheet.body.y >= ui.y+ui.results_footer.height-dp(1)
        assert self._on_keyboard(Window,27)  # Native Back closes the sheet first.
        for _ in range(8): yield
        assert not ui.saved_sheet.is_open and ui.manager.current=="results"
        self.check("Android regression: full Saved SMAs menu target opens a visible sheet; Back dismisses it")

        ui.show_settings()
        result = ui.model.result
        assert Window.dispatch("on_keyboard",27,None,None,[])  # Uses the real Window binding.
        assert ui.manager.current=="results" and ui.model.result is result, (
            ui.manager.current,ui._page_stack,[editor.focus for editor in ui.editors],
            [str(callback) for callback in Window.get_property_observers("on_keyboard")])
        ui.visible_crossovers=35
        ui.show_more_crossings()
        assert ui.manager.current=="crossovers"
        assert self._on_keyboard(Window,27)
        assert ui.manager.current=="results"
        assert self._on_keyboard(Window,27)
        assert ui.manager.current=="parameters"
        assert not self._on_keyboard(Window,27)  # Default Kivy handler may now exit.
        self.check("Android regression: native Back traverses full table/settings/results to Parameters; exit only there")

        # Real fields/layout, injected native geometry. Desktop has no Android IME.
        ui.show_settings()
        frame=self.device_frame
        for editor,value in ((ui.email_input,"reader@example.com"),(ui.alert_session,"273")):
            ui.settings_scroll.scroll_to(editor, padding=dp(20), animate=False)
            for _ in range(6): yield
            pointer=Pointer(*editor.to_window(*editor.center))
            pointer.down(); pointer.up()
            for _ in range(4): yield
            assert editor.focus
            frame.apply_metrics(WindowMetrics(top=int(dp(24)),bottom=int(dp(24)),keyboard=int(dp(300)),
                                             width=int(Window.width),height=int(Window.height)))
            for _ in range(8): yield
            assert editor.focus, "IME/layout changes must not clear editing focus"
            editor.select_all()
            for _ in range(2): yield
            Window.dispatch("on_textinput",value)
            assert editor.text==value, (editor.text,value,editor.selection_text)
            bottom=editor.to_window(editor.x,editor.y)[1]
            assert bottom>=ui.y-dp(1), ("Editor must remain above the injected keyboard",
                bottom,ui.pos,ui.size,ui.settings_scroll.pos,ui.settings_scroll.size,editor.pos,
                ui.settings_scroll.scroll_y)
            assert editor.to_window(editor.x,editor.top)[1]<=ui.top+dp(1)
            assert ui.settings_back_button.to_window(*ui.settings_back_button.center)[1]<Window.height-dp(24)
            assert self._on_keyboard(Window,27) and not editor.focus
            assert ui.manager.current=="settings"
            frame.apply_metrics(WindowMetrics(width=int(Window.width),height=int(Window.height)))
            for _ in range(6): yield
        ui.email_save_button.dispatch("on_release")
        assert ui.model.store.notification_settings().email=="reader@example.com"
        frame.metrics=None; frame._arrange()
        self.check("Android regression: email/EOD fields retain focus and accept text through keyboard/safe-area reflow; Back ends editing")

        # A fresh screen reads all committed rows without needing optimization,
        # including counters/scenarios different from the startup selection.
        ui.model.store.save("DEMO-US","Sideways",254,9)
        us_line=ui.model.store.list_lines("DEMO-US","Sideways")[0]
        ui.model.store.set_visible(us_line.id,False)
        expected_ids={line.id for line in ui.model.store.list_all_lines()}
        fresh=AnalyzerScreen(AnalyzerModel(LineStore(ui.model.store.path)))
        ui.close()
        frame.remove_widget(ui)
        frame.screen=self.screen=fresh
        frame.add_widget(fresh)
        frame._arrange()
        ui=fresh
        for _ in range(8): yield
        assert ui.manager.current=="parameters"
        assert set(ui.landing_saved_rows)==expected_ids
        assert all(row["hide"].text=="View" for row in ui.landing_saved_rows.values())
        ui.parameter_scroll.scroll_to(ui.landing_saved_rows[us_line.id]["hide"],animate=False)
        for _ in range(8): yield
        button=ui.landing_saved_rows[us_line.id]["hide"]
        pointer=Pointer(*button.to_window(*button.center))
        pointer.down(); pointer.up()
        for _ in range(8): yield
        assert ui.manager.current=="results" and ui.model.dataset.counter=="DEMO-US"
        assert ui.model.dataset.scenario=="Sideways" and ui.model.result.period==254
        assert ui.model.result.target_frequency==9 and ui.target.text=="Custom"
        assert ui.optimal_caption.text=="SAVED SMA"
        assert next(line for line in ui.chart.series if line.active).sma==ui.model.result.sma
        assert ui.saved_rows[us_line.id]["hide"].text=="Hide"
        assert set(ui.landing_saved_rows)==expected_ids
        ui.show_parameters()
        ui.parameter_scroll.scroll_y=1
        for _ in range(8): yield
        ui.export_to_png("artifacts/android-regression-landing.png")
        self.check("Android regression: fresh launch lists all saved SMAs; real View tap opens exact counter/scenario/period/custom target")


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
        report_name = "ui-android-regressions" if "--android-regressions-only" in sys.argv else "ui-smoke"
        Path(f"artifacts/{report_name}.json").write_text(json.dumps(report, indent=2) + "\n")
        temporary.cleanup()
    raise SystemExit(app.exit_code)
