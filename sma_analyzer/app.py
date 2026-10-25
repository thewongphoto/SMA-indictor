"""Portrait-first, offline Kivy application. Worker calculations never touch widgets."""
from concurrent.futures import ThreadPoolExecutor
import logging
import os
from pathlib import Path
import sqlite3

from kivy.config import Config

# A portrait desktop window is a convenient stand-in for the eventual phone UI.
Config.set("graphics", "width", "440")
Config.set("graphics", "height", "920")
Config.set("graphics", "resizable", "1")
Config.set("input", "mouse", "mouse,disable_multitouch")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput

from .chart import ACTIVE_COLOR, MUTED, PRICE_COLOR, PriceChart
from .engine import optimize_sma
from .model import AnalyzerModel
from .settings import ALLOW_CUSTOM_TARGET, COUNTERS, SCENARIOS, TARGET_FREQUENCIES
from .storage import LineStore

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


class ChoiceOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(48)
        self.font_size = sp(13)
        self.background_normal = ""
        self.background_color = (0.12, 0.17, 0.23, 1)


def choice(text, values):
    return Spinner(text=text, values=values, option_cls=ChoiceOption,
                   size_hint_y=None, height=dp(46), font_size=sp(13),
                   background_normal="", background_color=(0.12, 0.17, 0.23, 1), color=TEXT)


class AnalyzerScreen(AnchorLayout):
    def __init__(self, model, **kwargs):
        super().__init__(anchor_x="center", anchor_y="top", **kwargs)
        self.model = model
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sma")
        self.busy = False
        self.closed = False
        self._job = 0
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(3), size_hint=(None, 1))
        self.add_widget(self.scroll)
        self.bind(width=self._resize)
        self._resize()
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(14), padding=dp(16))
        self.content.bind(minimum_height=self.content.setter("height"))
        self.scroll.add_widget(self.content)

        self.content.add_widget(WrappedLabel(text="OFFLINE LAB  /  SIMULATED DATA", color=PRICE_COLOR,
                                            font_size=sp(11), bold=True))
        self.content.add_widget(WrappedLabel(text="SMA Stock Analyzer", font_size=sp(25), bold=True))
        self.content.add_widget(WrappedLabel(text="Explore crossing frequency. Save the lines you want to study.", color=MUTED))

        controls = Panel()
        self.content.add_widget(controls)
        controls.add_widget(WrappedLabel(text="01  /  CHOOSE YOUR SIMULATION", color=MUTED, font_size=sp(11), bold=True))
        controls.add_widget(WrappedLabel(text="Fictional counter · no real market prices"))
        self.counter = choice(model.dataset.counter, COUNTERS)
        controls.add_widget(self.counter)
        self.scenario = choice(model.dataset.scenario, SCENARIOS)
        controls.add_widget(self.scenario)
        controls.add_widget(WrappedLabel(text="Target upward crossings per trading year"))
        target_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        target_values = tuple(str(n) for n in TARGET_FREQUENCIES) + (("Custom",) if ALLOW_CUSTOM_TARGET else ())
        self.target = choice(str(model.target_frequency), target_values)
        target_row.add_widget(self.target)
        self.custom_target = TextInput(text="9", multiline=False, input_type="number",
                                       font_size=sp(16), padding=[dp(10), dp(12)],
                                       background_normal="", background_active="", background_color=(0.12, 0.17, 0.23, 1),
                                       foreground_color=TEXT, cursor_color=PRICE_COLOR)
        self.target_row = target_row
        controls.add_widget(target_row)
        self.optimize_button = LabButton(text="Optimize SMA", primary=True)
        self.optimize_button.bind(on_release=self.on_optimize)
        controls.add_widget(self.optimize_button)
        self.status = WrappedLabel(text="Choose a scenario, then press Optimize SMA.", color=MUTED)
        controls.add_widget(self.status)

        plot_panel = Panel()
        self.content.add_widget(plot_panel)
        self.plot_title = WrappedLabel(text="", bold=True, font_size=sp(15))
        plot_panel.add_widget(self.plot_title)
        self.plot_subtitle = WrappedLabel(text="", color=MUTED, font_size=sp(11))
        plot_panel.add_widget(self.plot_subtitle)
        self.chart = PriceChart(size_hint_y=None, height=dp(245))
        plot_panel.add_widget(self.chart)
        self.legend = WrappedLabel(text="", font_size=sp(11), color=MUTED)
        plot_panel.add_widget(self.legend)

        self.cards = GridLayout(cols=2, size_hint_y=None, spacing=dp(10))
        self.cards.bind(minimum_height=self.cards.setter("height"))
        self.card_values = {}
        for key, title in [("period", "SELECTED SMA"), ("target", "TARGET FREQUENCY"),
                           ("actual", "ACTUAL FREQUENCY"), ("count", "UPWARD CROSSINGS")]:
            card = Panel()
            card.add_widget(WrappedLabel(text=title, color=MUTED, font_size=sp(10)))
            value = WrappedLabel(text="—", bold=True, font_size=sp(19), color=ACTIVE_COLOR)
            card.add_widget(value)
            self.card_values[key] = value
            self.cards.add_widget(card)
        self.content.add_widget(self.cards)
        self.explanation = WrappedLabel(text="", color=MUTED, font_size=sp(12))
        self.content.add_widget(self.explanation)
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        self.save_button = LabButton(text="Save SMA line")
        self.hide_button = LabButton(text="Hide selected SMA")
        self.save_button.bind(on_release=self.on_save)
        self.hide_button.bind(on_release=self.on_active_visibility)
        actions.add_widget(self.save_button)
        actions.add_widget(self.hide_button)
        self.content.add_widget(actions)

        self.saved_panel = Panel()
        self.content.add_widget(self.saved_panel)
        self.table_panel = Panel()
        self.content.add_widget(self.table_panel)
        self.content.add_widget(WrappedLabel(
            text="Research tool only. Matching a crossing frequency does not establish profitability. "
                 "All prices are simulated; 252 sessions represent one trading year.",
            color=MUTED, font_size=sp(11)))

        self.counter.bind(text=self.on_dataset_change)
        self.scenario.bind(text=self.on_dataset_change)
        self.target.bind(text=self.on_target_change)
        self.custom_target.bind(text=self.on_custom_target)
        self.refresh()

    def _resize(self, *_):
        self.scroll.width = min(self.width, dp(580))

    def message(self, text, error=False):
        self.status.text = text
        self.status.color = ERROR if error else MUTED

    def on_dataset_change(self, *_):
        self._job += 1
        try:
            self.model.select_dataset(self.counter.text, self.scenario.text)
            self.message("Simulation changed. Press Optimize SMA to calculate a new result.")
            self.refresh()
        except (ValueError, sqlite3.Error, OSError) as error:
            self.message(f"Could not load simulation: {error}", True)

    def _read_target(self):
        self.model.set_target(self.custom_target.text if self.target.text == "Custom" else self.target.text)

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
            self.message("Optimization complete. Upward crossings are marked with triangles.")
        except (ValueError, sqlite3.Error, OSError) as error:
            self.message(f"Unable to optimize: {error}", True)
        except Exception:
            logging.exception("Unexpected optimization failure")
            self.message("Calculation failed unexpectedly. Try another simulation; details are in the log.", True)

    def on_save(self, *_):
        try:
            self.model.save_current()
            self.refresh()
            self.message("SMA line saved on this device for this counter and scenario.")
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
        data = self.model.dataset
        self.plot_title.text = f"{data.counter} · {data.scenario}"
        self.plot_subtitle.text = f"SIMULATED DATA · {len(data.prices)} sessions · fictional price units"
        lines = self.model.plot_lines()
        self.chart.update(data.prices, lines)
        self.legend.text = "Teal: simulated close   •   Triangles: upward crossings\n" + (
            "   /   ".join(f"{'Gold' if line.active else 'Saved'}: SMA {line.period}" for line in lines)
            if lines else "No SMA displayed. Optimize or show a saved line.")
        for key, value in self.model.summary().items():
            self.card_values[key].text = value
        self._set_busy(self.busy)
        self.hide_button.text = "Hide selected SMA" if self.model.active_visible else "Show selected SMA"
        result = self.model.result
        self.explanation.text = (
            f"Whole-history target: {result.target_crossings:g} crossings over {result.history_sessions} sessions. "
            f"Actual: {result.crossing_count}; absolute difference: {result.count_error:g}. "
            "Warm-up is included in the year length. Ties choose the shorter SMA."
            if result else "No optimization yet. Every candidate uses its available observations across the full history.")
        self._refresh_saved()
        self._refresh_table()

    def _refresh_saved(self):
        self.saved_panel.clear_widgets()
        self.saved_panel.add_widget(WrappedLabel(text="02  /  SAVED SMA LINES", font_size=sp(11), bold=True, color=MUTED))
        saved = self.model.saved_lines()
        if not saved:
            self.saved_panel.add_widget(WrappedLabel(text="No saved lines for this simulation. Optimize, then tap Save SMA line.", color=MUTED))
        for line in saved:
            self.saved_panel.add_widget(WrappedLabel(text=f"SMA {line.period} · target {line.target_frequency}/yr"))
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
            visible = line.visible
            if self.model.result and line.period == self.model.result.period:
                visible = self.model.active_visible
            toggle = LabButton(text="Hide" if visible else "Show")
            toggle.bind(on_release=lambda button, saved_line=line: self.on_saved_visibility(saved_line))
            delete = LabButton(text="Remove saved line")
            delete.bind(on_release=lambda button, saved_line=line: self.on_delete(saved_line))
            row.add_widget(toggle)
            row.add_widget(delete)
            self.saved_panel.add_widget(row)

    def _refresh_table(self):
        self.table_panel.clear_widgets()
        self.table_panel.add_widget(WrappedLabel(text="03  /  CROSSOVERS · SELECTED SMA", font_size=sp(11), bold=True, color=MUTED))
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
