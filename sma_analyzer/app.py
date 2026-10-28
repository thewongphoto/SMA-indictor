"""Portrait-first, offline Kivy application. Worker calculations never touch widgets."""
from concurrent.futures import ThreadPoolExecutor
import logging
import os
from pathlib import Path
import sqlite3
from dataclasses import replace

from kivy.config import Config

# A portrait desktop window is a convenient stand-in for the eventual phone UI.
Config.set("graphics", "width", "440")
Config.set("graphics", "height", "920")
Config.set("graphics", "resizable", "1")
Config.set("input", "mouse", "mouse,disable_multitouch")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.stacklayout import StackLayout
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

from .chart import ACTIVE_COLOR, MUTED, PRICE_COLOR, ChartScrollView, PriceChart
from .engine import optimize_sma
from .policy import maximum_sma_period
from .model import AnalyzerModel
from .settings import ALLOW_CUSTOM_TARGET, COUNTERS, SCENARIOS, TARGET_FREQUENCIES
from .storage import LineStore
from .viewport import available_timelines
from .widgets import TimelineSelector, RoundedSelector, LegendItem, LegendSymbol, IconButton, IconSymbol, RuleSwitch
from .notifications import evaluate_eod, deliver_alerts, AndroidNotifier, Alert

BG = (0.035, 0.055, 0.085, 1)
PANEL = (0.065, 0.095, 0.14, 1)
TEXT = (0.92, 0.95, 0.98, 1)
ERROR = (1, 0.52, 0.52, 1)


class WrappedLabel(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("font_size", sp(13))
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "middle")
        super().__init__(size_hint_y=None, **kwargs)
        self.bind(width=self._wrap, texture_size=self._height)
        self._wrap()

    def _wrap(self, *_):
        self.text_size = (self.width, None)

    def _height(self, *_):
        self.height = self.texture_size[1] + dp(4)


class LabButton(Button):
    def __init__(self, primary=False, **kwargs):
        super().__init__(background_normal="", background_down="", background_color=(0, 0, 0, 0),
                         color=BG if primary else TEXT, font_size=sp(13), bold=True,
                         size_hint_y=None, height=dp(44), **kwargs)
        self.fill = PRICE_COLOR if primary else (0.12, 0.17, 0.23, 1)
        with self.canvas.before:
            self._color = Color(*self.fill)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._draw, size=self._draw, state=self._draw, disabled=self._draw)

    def _draw(self, *_):
        self._rect.pos, self._rect.size = self.pos, self.size
        factor = 0.55 if self.disabled else 0.8 if self.state == "down" else 1
        self._color.rgba = (*[c * factor for c in self.fill[:3]], 1)


class Panel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(14), **kwargs)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(*PANEL)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self._rect.pos, self._rect.size = self.pos, self.size


def choice(text, values):
    return RoundedSelector(text=text, values=values)


class AnalyzerScreen(AnchorLayout):
    def __init__(self, model, **kwargs):
        super().__init__(anchor_x="center", anchor_y="top", **kwargs)
        with self.canvas.before:
            Color(*BG)
            self._background = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._paint_background, size=self._paint_background)
        self.model = model
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sma")
        self.busy = False
        self.closed = False
        self._job = 0
        self.scroll = ChartScrollView(do_scroll_x=False, bar_width=dp(3), size_hint=(None, 1))
        self.add_widget(self.scroll)
        self.bind(width=self._resize)
        self._resize()
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(14), padding=dp(16))
        with self.content.canvas.before:
            Color(*BG)
            content_background = Rectangle(pos=self.content.pos, size=self.content.size)
        def paint_content(*_):
            content_background.pos, content_background.size = self.content.pos, self.content.size
        self.content.bind(pos=paint_content, size=paint_content)
        self.content.bind(minimum_height=self.content.setter("height"))
        self.scroll.add_widget(self.content)

        header = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(3), padding=(dp(12), 0))
        self.header = header
        header.bind(minimum_height=header.setter("height"))
        self.content.add_widget(header)
        header.add_widget(WrappedLabel(text="OFFLINE LAB / SIMULATED DATA", color=MUTED,
                                            font_size=sp(11), bold=True))
        self.heading = WrappedLabel(text="SMA Stock Analyzer", font_size=sp(25), bold=True)
        header.add_widget(self.heading)
        self.introduction = WrappedLabel(text="Find the simple moving average (SMA) that matches a target upward crossing frequency.", color=MUTED)
        header.add_widget(self.introduction)

        controls = Panel()
        self.controls = controls
        self.content.add_widget(controls)
        self.control_grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(12))
        self.control_grid.bind(minimum_height=self.control_grid.setter("height"))
        controls.add_widget(self.control_grid)

        self.field_labels = []

        def field(title, widget):
            cell = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
            cell.bind(minimum_height=cell.setter("height"))
            label = WrappedLabel(text=title, color=MUTED, font_size=sp(10))
            self.field_labels.append(label)
            cell.add_widget(label)
            cell.add_widget(widget)
            self.control_grid.add_widget(cell)
            return cell

        self.counter = choice(model.dataset.counter, COUNTERS)
        field("COUNTER (FICTIONAL)", self.counter)
        self.scenario = choice(model.dataset.scenario, SCENARIOS)
        field("SCENARIO (FICTIONAL)", self.scenario)
        target_row = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        target_row.bind(minimum_height=target_row.setter("height"))
        target_values = tuple(f"{n} / year" for n in TARGET_FREQUENCIES) + (("Custom",) if ALLOW_CUSTOM_TARGET else ())
        self.target = choice(f"{model.target_frequency} / year", target_values)
        target_row.add_widget(self.target)
        self.custom_target = TextInput(text="9", multiline=False, input_type="number",
                                       size_hint_y=None, height=dp(44),
                                       font_size=sp(16), padding=[dp(10), dp(12)],
                                       background_normal="", background_active="", background_color=(0.12, 0.17, 0.23, 1),
                                       foreground_color=TEXT, cursor_color=PRICE_COLOR)
        self.target_row = target_row
        field("TARGET CROSSINGS", target_row)
        self.optimize_button = LabButton(text="Optimize SMA", primary=True)
        self.optimize_button.bind(on_release=self.on_optimize)
        self.optimize_cell = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(65))
        self.optimize_cell.add_widget(Label())
        self.optimize_cell.add_widget(self.optimize_button)
        self.control_grid.add_widget(self.optimize_cell)
        self.status = WrappedLabel(text="Choose a scenario, then press Optimize SMA.", color=MUTED)

        self.card_values = {}
        self.optimal_panel = Panel()
        self.optimal_value = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(3))
        self.optimal_value.bind(minimum_height=self.optimal_value.setter("height"))
        self.optimal_caption = WrappedLabel(text="OPTIMAL SMA", color=MUTED, font_size=sp(12))
        self.optimal_value.add_widget(self.optimal_caption)
        self.card_values["period"] = WrappedLabel(text="—", bold=True, font_size=sp(26), color=ACTIVE_COLOR)
        self.optimal_value.add_widget(self.card_values["period"])
        self.optimal_panel.add_widget(self.optimal_value)
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        self.optimal_actions = actions
        self.save_button = IconButton(kind="heart")
        self.hide_button = LabButton(text="Hide SMA line")
        self.save_button.bind(on_release=self.on_save)
        self.hide_button.bind(on_release=self.on_active_visibility)
        actions.add_widget(self.save_button)
        actions.add_widget(self.hide_button)
        self.optimal_panel.add_widget(actions)
        self.content.add_widget(self.optimal_panel)

        plot_panel = Panel()
        self.content.add_widget(plot_panel)
        self.plot_header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.plot_title = WrappedLabel(text="", bold=True, font_size=sp(15))
        self.plot_title.pos_hint = {"center_y": 0.5}
        self.plot_header.add_widget(self.plot_title)
        self.zoom_out_button = LabButton(text="Zoom out", size_hint_x=None, width=dp(92),
                                         pos_hint={"center_y": 0.5})
        self.zoom_out_button.height = dp(36)
        plot_panel.add_widget(self.plot_header)
        self.timeline_selector = TimelineSelector(values=("1Y", "Max"))
        plot_panel.add_widget(self.timeline_selector)
        self.plot_subtitle = WrappedLabel(text="", color=MUTED, font_size=sp(11))
        plot_panel.add_widget(self.plot_subtitle)
        self.chart = PriceChart(size_hint_y=None, height=dp(245))
        self.scroll.chart = self.chart
        self.zoom_out_button.bind(on_release=self.chart.reset_zoom)
        self.chart.bind(is_zoomed=self._refresh_chart_header, view_range=self._refresh_chart_header)
        plot_panel.add_widget(self.chart)
        self.timeline_selector.bind(on_select=lambda _, value: self.chart.set_timeline(value))
        plot_panel.add_widget(WrappedLabel(text="Drag across the plot to zoom.", font_size=sp(11), color=MUTED))
        legend_holder = AnchorLayout(size_hint_y=None, height=dp(24))
        self.legend = StackLayout(size_hint=(None, None), spacing=(dp(12), dp(2)))
        self.legend.bind(minimum_height=self.legend.setter("height"))
        self.legend.bind(height=lambda _, height: setattr(legend_holder, "height", height))
        legend_holder.add_widget(self.legend)
        plot_panel.add_widget(legend_holder)

        def center_legend(*_):
            self.legend.width = min(legend_holder.width, sum(child.width for child in self.legend.children)
                                    + dp(12) * max(0, len(self.legend.children) - 1))

        legend_holder.bind(width=center_legend)
        self.legend.bind(children=center_legend)
        self._center_legend = center_legend

        self.cards = GridLayout(cols=2, size_hint_y=None, spacing=dp(10))
        self.card_titles = []
        self.cards.bind(minimum_height=self.cards.setter("height"))
        for key, title in [("target", "TARGET CROSSING FREQUENCY"),
                           ("actual", "ACTUAL CROSSING FREQUENCY")]:
            card = Panel()
            label = WrappedLabel(text=title, color=MUTED, font_size=sp(10))
            self.card_titles.append(label)
            card.add_widget(label)
            value = WrappedLabel(text="—", bold=True, font_size=sp(19), color=ACTIVE_COLOR)
            card.add_widget(value)
            self.card_values[key] = value
            self.cards.add_widget(card)
        self.content.add_widget(self.cards)
        self.explanation = WrappedLabel(text="", color=MUTED, font_size=sp(12))
        self.content.add_widget(self.explanation)
        self.saved_panel = Panel()
        self.content.add_widget(self.saved_panel)
        self.table_panel = Panel()
        self.content.add_widget(self.table_panel)
        self._build_notification_settings()
        self.content.add_widget(WrappedLabel(
            text="Research tool only. Matching a crossing frequency does not establish profitability. "
                 "All prices are simulated; 252 sessions represent one trading year.",
            color=MUTED, font_size=sp(11)))

        self.counter.bind(text=self.on_dataset_change)
        self.scenario.bind(text=self.on_dataset_change)
        self.target.bind(text=self.on_target_change)
        self.custom_target.bind(text=self.on_custom_target)
        self.scroll.bind(width=self._layout_for_width)
        self._layout_for_width()
        self.refresh()

    def _resize(self, *_):
        self.scroll.width = min(self.width, dp(1000))

    def _paint_background(self, *_):
        self._background.pos, self._background.size = self.pos, self.size

    def _layout_for_width(self, *_):
        """Four compact controls on wide portraits; a readable 2×2 phone grid."""
        wide = self.scroll.width >= dp(760)
        self.control_grid.cols = 4 if wide else 2
        self.content.padding = (dp(26), dp(28)) if wide else (dp(16), dp(16))
        self.header.padding = (dp(20 if wide else 12), 0)
        self.heading.font_size = sp(32 if wide else 25)
        self.introduction.font_size = sp(16 if wide else 13)
        for label in self.field_labels:
            label.font_size = sp(12 if wide else 10)
        for widget in (self.counter, self.scenario, self.target, self.optimize_button,
                       self.save_button, self.hide_button):
            widget.font_size = sp(16 if wide else 13)
            widget.height = dp(52 if wide else 44)
        self.optimize_cell.height = dp(78 if wide else 65)
        self.save_button.width = dp(44)
        self.optimal_actions.height = dp(52 if wide else 44)
        self.optimal_caption.font_size = sp(14 if wide else 12)
        self.card_values["period"].font_size = sp(30 if wide else 26)
        for key in ("target", "actual"):
            self.card_values[key].font_size = sp(24 if wide else 19)
        for label in self.card_titles:
            label.font_size = sp(12 if wide else 10)
        self.plot_title.font_size = sp(18 if wide else 15)
        self.plot_subtitle.font_size = sp(13 if wide else 11)
        for panel in (self.controls, self.optimal_panel, self.chart.parent):
            panel.padding = dp(20 if wide else 14)
        side_by_side = self.scroll.width >= dp(620)
        self.optimal_panel.orientation = "horizontal" if side_by_side else "vertical"
        self.optimal_value.size_hint_x = 0.48 if side_by_side else 1
        self.optimal_actions.size_hint_x = 0.52 if side_by_side else 1
        self.optimal_actions.pos_hint = {"center_y": 0.5}
        # BoxLayout.minimum_height adds vertically only in vertical orientation.
        self.chart.height = dp(max(245, min(320, self.scroll.width * 0.33)))
        if hasattr(self,"saved_rows"):
            self._refresh_saved()

    def message(self, text, error=False, quiet=False):
        self.status.text = text
        self.status.color = ERROR if error else MUTED
        if quiet and self.status.parent is not None:
            self.controls.remove_widget(self.status)
        elif not quiet and self.status.parent is None:
            self.controls.add_widget(self.status)

    def on_dataset_change(self, *_):
        self._job += 1
        try:
            self.model.select_dataset(self.counter.text, self.scenario.text)
            self.message("Simulation changed. Press Optimize SMA to calculate a new result.")
            self.refresh()
        except (ValueError, sqlite3.Error, OSError) as error:
            self.message(f"Could not load simulation: {error}", True)

    def _read_target(self):
        self.model.set_target(self.custom_target.text if self.target.text == "Custom" else self.target.text.split(" / ")[0])

    def on_target_change(self, *_):
        if self.target.text == "Custom" and self.custom_target.parent is None:
            self.target_row.add_widget(self.custom_target)
        elif self.target.text != "Custom" and self.custom_target.parent is not None:
            self.target_row.remove_widget(self.custom_target)
        self._target_edited()

    def on_custom_target(self, *_):
        if self.target.text == "Custom":
            self._target_edited()

    def _target_edited(self):
        self._job += 1
        # Never leave stale statistics visible for a newly entered target.
        self.model.result = None
        try:
            self._read_target()
            self.message("Target changed. Press Optimize SMA to update the line.")
        except ValueError as error:
            self.message(str(error), True)
        self.refresh()

    def _set_busy(self, busy):
        self.busy = busy
        self.optimize_button.text = "Calculating…" if busy else "Optimize SMA"
        for widget in [self.optimize_button, self.counter, self.scenario, self.target, self.custom_target]:
            widget.disabled = busy
        self.save_button.disabled = busy or self.model.result is None
        self.hide_button.disabled = busy or self.model.result is None

    def on_optimize(self, *_):
        if self.busy:
            return
        try:
            self._read_target()
        except ValueError as error:
            self.message(str(error), True)
            return
        self._job += 1
        token = self._job
        self._set_busy(True)
        self.message("Calculating all candidate periods across the full simulated history…")
        future = self.executor.submit(optimize_sma, self.model.dataset.prices, self.model.target_frequency)
        future.add_done_callback(lambda completed: Clock.schedule_once(
            lambda _dt: self._complete(completed, token), 0))

    def _complete(self, future, token):
        if self.closed:
            return
        self._set_busy(False)
        if token != self._job:
            return
        try:
            self.model.apply_result(future.result())
            self.refresh()
            self.message("Optimization complete. Upward crossings are marked with outlined plus signs.", quiet=True)
        except (ValueError, sqlite3.Error, OSError) as error:
            self.message(f"Unable to optimize: {error}", True)
        except Exception:
            logging.exception("Unexpected optimization failure")
            self.message("Calculation failed unexpectedly. Try another simulation; details are in the log.", True)

    def on_save(self, *_):
        try:
            saved = self.model.toggle_current_saved()
            self.refresh()
            self.message("SMA line saved on this device." if saved else "SMA line unsaved. Restore it from the last-10 history.")
        except (ValueError, sqlite3.Error, OSError) as error:
            self.message(f"Could not save line: {error}. Check local storage permissions.", True)

    def on_active_visibility(self, *_):
        self.model.active_visible = not self.model.active_visible
        self.refresh()

    def on_saved_visibility(self, line, *_):
        try:
            current = line.visible
            if self.model.result and line.period == self.model.result.period:
                current = self.model.active_visible
            visible = not current
            self.model.store.set_visible(line.id, visible)
            if self.model.result and line.period == self.model.result.period:
                self.model.active_visible = visible
            self.refresh()
        except (sqlite3.Error, OSError) as error:
            self.message(f"Could not change saved line: {error}", True)

    def on_delete(self, line, *_):
        try:
            self.model.store.delete(line.id)
            self.refresh()
        except (sqlite3.Error, OSError) as error:
            self.message(f"Could not remove saved line: {error}", True)

    def refresh(self):
        self.last_alerts = ()
        self.alert_preview.text = "No current preview. Choose a session and press Preview EOD alerts."
        data = self.model.dataset
        self.alert_session_label.text = f"Test an end-of-day session (1–{len(data.prices)})"
        self.plot_title.text = f"{data.counter} · {data.scenario}"
        lines = self.model.plot_lines()
        self.chart.update(data.prices, lines)
        self._refresh_chart_header()
        self.legend.clear_widgets()
        self.legend_labels = ["simulated close", "upward crossings"]
        def add_legend(text, color, plus=False):
            item = LegendItem(text, color, plus=plus)
            item.bind(width=self._center_legend)
            self.legend.add_widget(item)

        add_legend("simulated close", PRICE_COLOR)
        add_legend("upward crossings", ACTIVE_COLOR, plus=True)
        for index, line in enumerate(lines):
            label = f"SMA {line.period}"
            self.legend_labels.append(label)
            add_legend(label, self.chart.line_color(line, index))
        for key, value in self.model.summary().items():
            if key in self.card_values:
                self.card_values[key].text = value
        self._set_busy(self.busy)
        self.save_button.selected = self.model.current_saved_line() is not None
        self.hide_button.text = "Hide SMA line" if self.model.active_visible else "Show SMA line"
        result = self.model.result
        self.explanation.text = (
            f"Based on {result.comparisons} usable comparisons "
            f"({result.usable_years:.2f} trading years) from {result.history_sessions} sessions. "
            f"Target difference: {float(result.frequency_error):.2f}/yr. "
            f"SMA search: 2–{maximum_sma_period(result.history_sessions)}. "
            "Warm-up and gaps are excluded. Ties choose the shorter SMA. "
            + ("Closest eligible result; target not matched exactly." if result.frequency_error else "Target matched.")
            if result else "Optimize across all observable history. Warm-up and gaps are excluded from annual frequency.")
        self._refresh_saved()
        self._refresh_table()

    def _refresh_chart_header(self, *_):
        if self.chart.is_zoomed:
            if self.zoom_out_button.parent is None:
                self.plot_header.add_widget(self.zoom_out_button)
        elif self.zoom_out_button.parent is not None:
            self.plot_header.remove_widget(self.zoom_out_button)
        data = self.model.dataset
        self.timeline_selector.values = available_timelines(len(data.prices))
        self.timeline_selector.text = self.chart.timeline
        self.timeline_selector.disabled = not data.prices
        self.plot_subtitle.text = f"SIMULATED DATA · {len(data.prices)} sessions · fictional price units"
        if data.prices:
            start, end = self.chart.view_range
            self.plot_subtitle.text += f"\n{self.chart.timeline} view · sessions {start + 1}–{end + 1}"

    def _refresh_saved(self):
        self.saved_panel.clear_widgets()
        header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        header.add_widget(WrappedLabel(text="02  /  SAVED SMA LINES", font_size=sp(11), bold=True, color=MUTED))
        self.history_button = IconButton(kind="history")
        self.history_button.bind(on_release=self.open_unsaved_history)
        header.add_widget(self.history_button)
        self.saved_panel.add_widget(header)
        saved = self.model.saved_lines()
        self.saved_rows = {}
        if not saved:
            self.saved_panel.add_widget(WrappedLabel(text="No saved lines for this simulation. Optimize, then tap the heart.", color=MUTED))
        for line in saved:
            label = f"SMA {line.period} · target {line.target_frequency}/yr"
            if len(self.model.dataset.prices) >= 4 and line.period > maximum_sma_period(len(self.model.dataset.prices)):
                label += " · saved previously; outside current search limit"
            title = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(5))
            active = self.model.result is not None and self.model.result.period == line.period
            swatch = LegendSymbol(self.chart.period_color(line.period, active))
            title.add_widget(swatch)
            title_label = WrappedLabel(text=label)
            title.add_widget(title_label)
            title_label.bind(height=lambda _, height, box=title: setattr(box, "height", max(dp(28), height)))
            self.saved_panel.add_widget(title)
            # At phone widths two left controls share a row; hide/heart stay at right below.
            row = GridLayout(cols=4 if self.scroll.width >= dp(620) else 2,
                             size_hint_y=None, spacing=dp(6))
            row.bind(minimum_height=row.setter("height"))
            push = LabButton(text="Push notifications " + ("On" if line.push_enabled else "Off"))
            email = LabButton(text="Email notifications " + ("On" if line.email_enabled else "Off"))
            for button, enabled in ((push,line.push_enabled),(email,line.email_enabled)):
                button.font_size = sp(11)
                button.text_size = (None, None)
                if enabled:
                    button.fill = (0.12,0.35,0.32,1)
                    button._draw()
            push.bind(on_release=lambda _, saved_line=line: self.on_line_alert(saved_line,"phone"))
            email.bind(on_release=lambda _, saved_line=line: self.on_line_alert(saved_line,"email"))
            visible = self.model.active_visible if active else line.visible
            toggle = LabButton(text="Hide" if visible else "Show", size_hint_x=None, width=dp(64))
            toggle.bind(on_release=lambda _, saved_line=line: self.on_saved_visibility(saved_line))
            heart = IconButton(kind="heart", selected=True)
            heart.bind(on_release=lambda _, saved_line=line: self.on_delete(saved_line))
            if row.cols == 4:
                row.add_widget(push)
                row.add_widget(email)
                row.add_widget(toggle)
                row.add_widget(heart)
            else:
                # Full-width notification row, then a right-aligned compact action row.
                row.add_widget(push)
                row.add_widget(email)
                actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
                actions.add_widget(Label())
                actions.add_widget(toggle)
                actions.add_widget(heart)
                self.saved_panel.add_widget(row)
                self.saved_panel.add_widget(actions)
            if row.cols == 4:
                self.saved_panel.add_widget(row)
            self.saved_rows[line.id] = dict(push=push,email=email,hide=toggle,heart=heart,swatch=swatch)

    def on_line_alert(self, line, channel):
        enabled = line.push_enabled if channel == "phone" else line.email_enabled
        try:
            self.model.store.set_notifications(line.id,channel,not enabled)
            self.refresh()
        except (ValueError,sqlite3.Error) as error:
            self.notification_status.text = str(error)
            content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
            content.add_widget(WrappedLabel(text=str(error)))
            go = LabButton(text="Open notification settings")
            content.add_widget(go)
            self.validation_popup = Popup(title="Notification settings", content=content,
                                          size_hint=(.9,None),height=dp(210))
            go.bind(on_release=lambda _: (self.validation_popup.dismiss(),
                                         self.scroll.scroll_to(self.settings_panel,animate=False)))
            self.validation_popup.open()

    def open_unsaved_history(self, *_):
        content = BoxLayout(orientation="vertical", spacing=dp(10),padding=dp(10))
        content.add_widget(WrappedLabel(text="Last 10 unsaved lines · all counters/scenarios. Older entries are discarded.",color=MUTED))
        scroll = ScrollView(do_scroll_x=False)
        entries = BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(10))
        entries.bind(minimum_height=entries.setter("height"))
        self.history_restore_buttons = {}
        for line in self.model.store.recent_unsaved():
            label = WrappedLabel(text=f"{line.counter} · {line.scenario} · SMA {line.period} · target {line.target_frequency}/yr")
            entries.add_widget(label)
            restore = LabButton(text="Restore saved line")
            restore.bind(on_release=lambda _, entry=line: self.restore_unsaved(entry))
            entries.add_widget(restore)
            self.history_restore_buttons[line.id] = restore
        if not self.history_restore_buttons:
            entries.add_widget(WrappedLabel(text="No unsaved lines yet. Only lines you saved and then unsaved appear here."))
        scroll.add_widget(entries)
        content.add_widget(scroll)
        self.history_status = WrappedLabel(text="",color=ERROR,font_size=sp(11))
        content.add_widget(self.history_status)
        close = LabButton(text="Close")
        content.add_widget(close)
        self.history_popup = Popup(title="Recently unsaved SMA lines",content=content,size_hint=(.94,.8))
        close.bind(on_release=self.history_popup.dismiss)
        self.history_popup.open()

    def restore_unsaved(self, line):
        try:
            self.model.store.restore(line.id)
            self.history_popup.dismiss()
            self.refresh()
            self.message(f"Restored SMA {line.period} for {line.counter} · {line.scenario}.")
        except (ValueError,sqlite3.Error) as error:
            self.history_status.text = str(error)

    def _build_notification_settings(self):
        self.settings_panel = Panel()
        self.content.add_widget(self.settings_panel)
        self.settings_panel.add_widget(WrappedLabel(text="04  /  NOTIFICATION SETTINGS",bold=True,color=MUTED,font_size=sp(11)))
        self.settings_panel.add_widget(WrappedLabel(text="SIMULATED DATA · Manual EOD tests only. No background monitoring. Email stays in preview mode.",color=MUTED,font_size=sp(11)))
        settings = self.model.store.notification_settings()
        self.notification_switches = {}
        descriptions = {
            "buy": ("Buy signal: Upward crossing detected", "Triggers an alert when the end-of-day price crosses above a SMA."),
            "monitor": ("Impending buy signal", "Triggers an alert once per EOD session when the close is strictly below a SMA."),
        }
        for channel, icon, title in (("phone","phone","Phone notifications"),("email","mail","Email notifications")):
            heading = BoxLayout(size_hint_y=None,height=dp(28),spacing=dp(6))
            heading.add_widget(IconSymbol(icon))
            heading.add_widget(WrappedLabel(text=title,bold=True))
            self.settings_panel.add_widget(heading)
            for kind in ("buy","monitor"):
                key = f"{channel}_{kind}"
                row = BoxLayout(size_hint_y=None,spacing=dp(8))
                row.bind(minimum_height=row.setter("height"))
                words = BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(2))
                words.bind(minimum_height=words.setter("height"))
                name, description = descriptions[kind]
                words.add_widget(WrappedLabel(text=name))
                words.add_widget(WrappedLabel(text=description,color=MUTED,font_size=sp(11)))
                row.add_widget(words)
                switch = RuleSwitch(active=getattr(settings,key))
                switch.bind(active=lambda _, active, field=key: self.on_notification_rule(field,active))
                row.add_widget(switch)
                self.notification_switches[key] = switch
                self.settings_panel.add_widget(row)
        self.settings_panel.add_widget(WrappedLabel(text="Email address · saved only on this device",color=MUTED,font_size=sp(11)))
        address_row = BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(8))
        self.email_input = TextInput(text=settings.email,multiline=False,font_size=sp(13),
                                    padding=(dp(8),dp(12)),write_tab=False,
                                    background_normal="",background_active="",background_color=(.12,.17,.23,1),
                                    foreground_color=TEXT,cursor_color=PRICE_COLOR)
        self.email_save_button = LabButton(text="Save",size_hint_x=None,width=dp(68))
        self.email_save_button.bind(on_release=self.on_save_email)
        address_row.add_widget(self.email_input)
        address_row.add_widget(self.email_save_button)
        self.settings_panel.add_widget(address_row)
        self.notification_status = WrappedLabel(text="Email previews never send messages. Enable a type above and a channel on each saved line.",color=MUTED,font_size=sp(11))
        self.settings_panel.add_widget(self.notification_status)
        self.alert_session_label = WrappedLabel(text="Test an end-of-day session (1–1260)",color=MUTED,font_size=sp(11))
        self.settings_panel.add_widget(self.alert_session_label)
        test_row = BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(8))
        self.alert_session = TextInput(text="1260",multiline=False,input_filter="int",font_size=sp(13),
                                      size_hint_x=None,width=dp(70),padding=(dp(8),dp(12)),
                                      background_normal="",background_active="",background_color=(.12,.17,.23,1),
                                      foreground_color=TEXT,cursor_color=PRICE_COLOR)
        self.preview_alert_button = LabButton(text="Preview EOD alerts")
        self.preview_alert_button.bind(on_release=self.preview_eod_alerts)
        test_row.add_widget(self.alert_session)
        test_row.add_widget(self.preview_alert_button)
        self.settings_panel.add_widget(test_row)
        self.phone_test_button = LabButton(text="Test Android phone notification")
        self.phone_test_button.bind(on_release=self.test_phone_notification)
        self.settings_panel.add_widget(self.phone_test_button)
        self.eod_deliver_button = LabButton(text="Show enabled EOD phone alerts (Android)")
        self.eod_deliver_button.font_size = sp(11)
        self.eod_deliver_button.bind(on_release=self.deliver_eod_alerts)
        self.settings_panel.add_widget(self.eod_deliver_button)
        self.alert_preview = WrappedLabel(text="No alert preview yet.",color=MUTED,font_size=sp(12))
        self.settings_panel.add_widget(self.alert_preview)
        self.last_alerts = ()

    def on_notification_rule(self, key, active):
        if getattr(self,"_reverting_rule",False):
            return
        try:
            settings = replace(self.model.store.notification_settings(), **{key:active})
            self.model.store.save_notification_settings(settings)
            self.last_alerts = ()
            self.alert_preview.text = "Notification types changed. Press Preview EOD alerts to refresh."
        except (ValueError,sqlite3.Error) as error:
            self._reverting_rule = True
            self.notification_switches[key].active = not active
            self._reverting_rule = False
            self.notification_status.text = str(error)

    def on_save_email(self, *_):
        try:
            settings = replace(self.model.store.notification_settings(),email=self.email_input.text)
            self.model.store.save_notification_settings(settings)
            self.email_input.text = settings.email.strip()
            self.notification_status.text = "Email address saved locally. Email remains preview-only."
        except (ValueError,sqlite3.Error) as error:
            self.notification_status.text = str(error)

    def preview_eod_alerts(self, *_):
        try:
            self.notification_status.text = "Preview only · no notification or email was sent."
            try:
                session = int(self.alert_session.text)
            except ValueError:
                raise ValueError("Enter a valid EOD session number, such as 1260.") from None
            settings = self.model.store.notification_settings()
            self.last_alerts = tuple(alert for line in self.model.saved_lines()
                                    for alert in evaluate_eod(self.model.dataset.prices,line,settings,session))
            self.alert_preview.text = ("\n\n".join(
                f"{alert.channel.upper()} PREVIEW · {alert.subject}\n{alert.body}" for alert in self.last_alerts)
                or "No alerts at this close. Check saved-line channels, notification types, session and SMA warm-up.")
            if not self.model.saved_lines():
                self.alert_preview.text = "Save an SMA line with the heart before testing notifications."
            return self.last_alerts
        except (ValueError,sqlite3.Error) as error:
            self.last_alerts = ()
            self.alert_preview.text = str(error) if str(error) else "Enter a valid EOD session number."
            return ()

    def test_phone_notification(self, *_):
        try:
            AndroidNotifier.request_permission()
            alert = Alert("phone","test",self.model.dataset.counter,self.model.dataset.scenario,2,12,0,
                          "SMA Stock Analyzer · Test", "SIMULATED TEST · Phone notifications are working.")
            # Permission dialog is asynchronous. Press again after granting it.
            AndroidNotifier().send(alert)
            self.notification_status.text = "Android test notification posted. Check the notification shade."
        except Exception as error:
            self.notification_status.text = (str(error) if isinstance(error,RuntimeError)
                                             else "Android notification failed. Check permission and device setup.")

    def deliver_eod_alerts(self, *_):
        alerts = self.preview_eod_alerts()
        if alerts:
            self.eod_deliver_button.disabled = True
            future = self.executor.submit(deliver_alerts,self.model.store,alerts)
            future.add_done_callback(lambda completed: Clock.schedule_once(
                lambda _: self._finish_alert_delivery(completed),0))

    def _finish_alert_delivery(self, future):
        if self.closed:
            return
        self.eod_deliver_button.disabled = False
        try:
            self.notification_status.text = "\n".join(future.result())
        except Exception:
            self.notification_status.text = "Delivery failed. Check Android notification setup; email remains preview-only."

    def _refresh_table(self):
        self.table_panel.clear_widgets()
        self.table_panel.add_widget(WrappedLabel(text="03  /  CROSSOVERS · SELECTED SMA", font_size=sp(11), bold=True, color=MUTED))
        self.crossing_count_label = WrappedLabel(
            text=(f"{self.model.result.crossing_count} upward crossings across all observable history"
                  if self.model.result else "Optimize to calculate upward crossings."),
            color=ACTIVE_COLOR, bold=True)
        self.table_panel.add_widget(self.crossing_count_label)
        rows = self.model.event_rows()
        if not rows:
            self.table_panel.add_widget(WrappedLabel(
                text="No upward crossings for the selected SMA." if self.model.result else "Optimize to list crossover events.", color=MUTED))
            return
        table = GridLayout(cols=3, size_hint_y=None, row_default_height=dp(30), row_force_default=True, spacing=dp(3))
        table.bind(minimum_height=table.setter("height"))
        for title in ["Session", "Sim. close", "SMA"]:
            table.add_widget(Label(text=title, color=MUTED, font_size=sp(12)))
        for row in rows:
            for value in row:
                table.add_widget(Label(text=value, color=TEXT, font_size=sp(12)))
        self.table_panel.add_widget(table)

    def close(self):
        self.closed = True
        self.executor.shutdown(wait=False, cancel_futures=True)


class SMAStockAnalyzerApp(App):
    title = "SMA Stock Analyzer"

    def build(self):
        Window.clearcolor = BG
        Window.minimum_width = dp(320)
        Window.minimum_height = dp(480)
        try:
            # Avoid evaluating user_data_dir when an explicit writable path is supplied.
            configured = os.environ.get("SMA_ANALYZER_DATA_DIR")
            directory = Path(configured if configured else self.user_data_dir)
            self.screen = AnalyzerScreen(AnalyzerModel(LineStore(directory / "saved_lines.sqlite3")))
        except (sqlite3.Error, OSError) as error:
            return WrappedLabel(text=f"Local storage could not be opened: {error}\n"
                                "Choose a writable SMA_ANALYZER_DATA_DIR and restart.", color=ERROR)
        return self.screen

    def on_stop(self):
        if hasattr(self, "screen"):
            self.screen.close()
