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
from kivy.uix.screenmanager import Screen, ScreenManager, NoTransition
from .navigation import SavedLinesSheet

from .chart import ACTIVE_COLOR, MUTED, PRICE_COLOR, ChartScrollView, PriceChart
from .engine import optimize_sma
from .policy import maximum_sma_period
from .model import AnalyzerModel
from .settings import ALLOW_CUSTOM_TARGET, COUNTERS, SCENARIOS, TARGET_FREQUENCIES, GMAIL_SENDER_ADDRESS
from .storage import LineStore
from .viewport import available_timelines
from .widgets import TimelineSelector, RoundedSelector, LegendItem, LegendSymbol, IconButton, IconSymbol, RuleSwitch
from .notifications import evaluate_eod, deliver_alerts, AndroidNotifier, Alert
from .gmail import GmailSender
from .android_gmail import AndroidGmailAuthorizer

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
        self.gmail_sender = GmailSender(GMAIL_SENDER_ADDRESS)
        self.gmail_authorizer = AndroidGmailAuthorizer()
        self.delivery_busy = False
        self.manager = ScreenManager(transition=NoTransition())
        self.add_widget(self.manager)
        self.pages = {}
        for name in ("parameters", "results", "crossovers", "settings"):
            page = Screen(name=name)
            self.pages[name] = page
            self.manager.add_widget(page)
        self.scroll, self.content = self._scrolling_page("results", chart=True, footer=True)
        self.parameter_scroll, self.parameter_content = self._scrolling_page("parameters")
        self.settings_scroll, self.settings_content = self._scrolling_page("settings")
        self.full_crossovers_scroll, self.full_crossovers_content = self._scrolling_page("crossovers")
        self.bind(width=self._resize)
        self._resize()
        self.visible_crossovers = 5
        self._table_result = None

        header = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(3), padding=(dp(12), 0))
        self.header = header
        header.bind(minimum_height=header.setter("height"))
        self.parameter_content.add_widget(header)
        header.add_widget(WrappedLabel(text="OFFLINE LAB / SIMULATED DATA", color=MUTED,
                                            font_size=sp(11), bold=True))
        self.heading = WrappedLabel(text="SMA Stock Analyzer", font_size=sp(25), bold=True)
        header.add_widget(self.heading)
        self.introduction = WrappedLabel(text="Find the simple moving average (SMA) that matches a target upward crossing frequency.", color=MUTED)
        header.add_widget(self.introduction)

        controls = Panel()
        self.controls = controls
        self.parameter_content.add_widget(controls)
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
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.optimal_actions = actions
        self.save_button = IconButton(kind="heart")
        self.hide_button = LabButton(text="Hide SMA", size_hint_x=None, width=dp(88))
        self.change_parameters_button = LabButton(text="Change parameters")
        self.change_parameters_button.font_size = sp(11)
        self.change_parameters_button.bind(on_release=self.show_parameters)
        self.save_button.bind(on_release=self.on_save)
        self.hide_button.bind(on_release=self.on_active_visibility)
        actions.add_widget(self.save_button)
        actions.add_widget(self.hide_button)
        actions.add_widget(self.change_parameters_button)
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
        self.saved_sheet = SavedLinesSheet(self, self.saved_panel)
        self.saved_sheet.bind(is_open=lambda _, opened: setattr(self.saved_menu_button,"kind","down" if opened else "menu"))
        self.table_panel = Panel()
        self.content.add_widget(self.table_panel)
        self.settings_back_button = self._page_heading("settings","Notification settings")
        self.crossovers_back_button = self._page_heading("crossovers","All upward crossings")
        self.full_table_panel = Panel()
        self.full_crossovers_content.add_widget(self.full_table_panel)
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
        self.manager.current = "parameters"

    def _scrolling_page(self, name, chart=False, footer=False):
        """Each page keeps its own scroll offset; only Results routes plot gestures."""
        column = BoxLayout(orientation="vertical")
        self.pages[name].add_widget(column)
        anchor = AnchorLayout(anchor_x="center", anchor_y="top")
        column.add_widget(anchor)
        scroll = (ChartScrollView if chart else ScrollView)(do_scroll_x=False,
                    bar_width=dp(3), size_hint=(None, 1))
        anchor.add_widget(scroll)
        content = BoxLayout(orientation="vertical", size_hint_y=None,
                            spacing=dp(14), padding=dp(16))
        with content.canvas.before:
            Color(*BG)
            background = Rectangle(pos=content.pos,size=content.size)
        def paint_content(*_):
            background.pos, background.size = content.pos, content.size
        content.bind(pos=paint_content,size=paint_content)
        content.bind(minimum_height=content.setter("height"))
        scroll.add_widget(content)
        if footer:
            self.results_footer = BoxLayout(orientation="vertical",size_hint_y=None,
                                            spacing=dp(4),padding=(dp(16),dp(6)))
            self.results_footer.bind(minimum_height=self.results_footer.setter("height"))
            bar = BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(8))
            self.saved_menu_button = IconButton(kind="menu")
            self.saved_menu_button.bind(on_release=self.toggle_saved_sheet)
            bar.add_widget(self.saved_menu_button)
            bar.add_widget(WrappedLabel(text="Saved SMAs",pos_hint={"center_y":.5}))
            self.settings_button = IconButton(kind="settings")
            self.settings_button.bind(on_release=self.show_settings)
            bar.add_widget(self.settings_button)
            self.results_footer.add_widget(bar)
            self.results_feedback = WrappedLabel(text="",color=MUTED,font_size=sp(11))
            column.add_widget(self.results_footer)
        return scroll, content

    def _page_heading(self, page_name, title):
        # Keep Back reachable even at the bottom of a long event list/settings.
        row = BoxLayout(size_hint_y=None,height=dp(56),spacing=dp(8),padding=(dp(16),dp(6)))
        button = IconButton(kind="back")
        button.bind(on_release=self.show_results)
        row.add_widget(button)
        row.add_widget(WrappedLabel(text=title,bold=True,font_size=sp(18),pos_hint={"center_y":.5}))
        column = self.pages[page_name].children[0]
        column.add_widget(row,index=len(column.children))
        return button

    def _resize(self, *_):
        for scroll in (self.scroll,self.parameter_scroll,self.settings_scroll,self.full_crossovers_scroll):
            scroll.width = min(self.width, dp(1000))

    def show_parameters(self, *_):
        self.saved_sheet.dismiss(animate=False)
        self.manager.current = "parameters"
        self.parameter_scroll.scroll_y = 1

    def show_results(self, *_):
        self.saved_sheet.dismiss(animate=False)
        self.manager.current = "results"

    def show_settings(self, *_):
        self.saved_sheet.dismiss(animate=False)
        self.manager.current = "settings"

    def toggle_saved_sheet(self, *_):
        if self.saved_sheet.is_open:
            self.saved_sheet.dismiss()
        else:
            self.saved_sheet.open()

    def _paint_background(self, *_):
        self._background.pos, self._background.size = self.pos, self.size

    def _layout_for_width(self, *_):
        """Four compact controls on wide portraits; a readable 2×2 phone grid."""
        wide = self.scroll.width >= dp(760)
        self.control_grid.cols = 4 if wide else 2
        for content in (self.content,self.parameter_content,self.settings_content,self.full_crossovers_content):
            content.padding = (dp(26), dp(28)) if wide else (dp(16), dp(16))
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
        self.hide_button.width = dp(88)
        self.change_parameters_button.font_size = sp(13 if wide else 11)
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
        self.results_feedback.text = text
        self.results_feedback.color = ERROR if error else MUTED
        if quiet and self.results_feedback.parent is not None:
            self.results_footer.remove_widget(self.results_feedback)
        elif not quiet and self.manager.current == "results" and self.results_feedback.parent is None:
            self.results_footer.add_widget(self.results_feedback, index=1)
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
        self.show_parameters()
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
            self.show_results()
            self.scroll.scroll_y = 1
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
            if saved:
                self.saved_sheet.open()
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
        self.hide_button.text = "Hide SMA" if self.model.active_visible else "Show SMA"
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
                                         self.show_settings()))
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
        self.settings_content.add_widget(self.settings_panel)
        self.settings_panel.add_widget(WrappedLabel(text="04  /  NOTIFICATION SETTINGS",bold=True,color=MUTED,font_size=sp(11)))
        self.settings_panel.add_widget(WrappedLabel(text="SIMULATED DATA · Manual EOD tests. Preview sends nothing; Send enabled alerts can post phone alerts and email through Gmail.",color=MUTED,font_size=sp(11)))
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
        self.settings_panel.add_widget(WrappedLabel(text=f"Gmail sender: {GMAIL_SENDER_ADDRESS}",color=MUTED,font_size=sp(11)))
        self.gmail_status = WrappedLabel(text="Gmail not connected. Google sign-in is required on Android.",color=MUTED,font_size=sp(11))
        self.settings_panel.add_widget(self.gmail_status)
        gmail_row = BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(8))
        self.gmail_connect_button = LabButton(text="Connect Gmail")
        self.gmail_disconnect_button = LabButton(text="Disconnect")
        self.gmail_connect_button.bind(on_release=self.connect_gmail)
        self.gmail_disconnect_button.bind(on_release=self.disconnect_gmail)
        gmail_row.add_widget(self.gmail_connect_button)
        gmail_row.add_widget(self.gmail_disconnect_button)
        self.settings_panel.add_widget(gmail_row)
        self.gmail_test_button = LabButton(text="Send a test email via Gmail")
        self.gmail_test_button.bind(on_release=self.test_gmail_email)
        self.settings_panel.add_widget(self.gmail_test_button)
        self.settings_panel.add_widget(WrappedLabel(text="Recipient email address · saved only on this device",color=MUTED,font_size=sp(11)))
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
        self.notification_status = WrappedLabel(text="Preview sends nothing. Send enabled alerts sends selected channels; email needs Google authorization.",color=MUTED,font_size=sp(11))
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
        self.eod_deliver_button = LabButton(text="Send enabled alerts")
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
            self.notification_status.text = "Recipient saved locally. Preview sends nothing; Gmail sending requires authorization."
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

    def _on_ui(self, callback):
        Clock.schedule_once(lambda _: callback() if not self.closed else None, 0)

    def test_phone_notification(self, *_):
        def permitted(allowed):
            self._on_ui(lambda: self._post_test_phone(allowed))
        try:
            AndroidNotifier.request_permission(permitted)
        except RuntimeError as error:
            self.notification_status.text = str(error)

    def _post_test_phone(self, allowed):
        if not allowed:
            self.notification_status.text = "Notification permission denied. Enable it in Android Settings to test again."
            return
        try:
            alert = Alert("phone","test",self.model.dataset.counter,self.model.dataset.scenario,2,12,0,
                          "SMA Stock Analyzer · Test", "SIMULATED TEST · Phone notifications are working.")
            AndroidNotifier().send(alert)
            self.notification_status.text = "Android test notification posted. Check the notification shade."
        except RuntimeError as error:
            self.notification_status.text = str(error)

    def _delivery_controls(self, busy):
        self.delivery_busy = busy
        for widget in (self.eod_deliver_button,self.gmail_connect_button,self.gmail_disconnect_button,
                       self.gmail_test_button,self.email_input,self.email_save_button):
            widget.disabled = busy

    def connect_gmail(self, *_):
        self._delivery_controls(True)
        self.gmail_status.text = "Waiting for Google authorization…"
        try:
            self.gmail_authorizer.authorize(GMAIL_SENDER_ADDRESS,
                lambda token: self._on_ui(lambda: self._gmail_connected(token)),
                lambda message: self._on_ui(lambda: self._gmail_connect_failed(message)))
        except RuntimeError as error:
            self._gmail_connect_failed(str(error))

    def _gmail_connected(self, token):
        self.gmail_sender.accept_access_token(token)
        self.gmail_status.text = f"Connected for sending as {GMAIL_SENDER_ADDRESS}. No inbox access requested."
        self._delivery_controls(False)

    def _gmail_connect_failed(self, message):
        self.gmail_sender.disconnect()
        self.gmail_status.text = message
        self._delivery_controls(False)

    def disconnect_gmail(self, *_):
        self.gmail_sender.disconnect()
        self._delivery_controls(True)
        try:
            self.gmail_authorizer.revoke(GMAIL_SENDER_ADDRESS,
                lambda: self._on_ui(lambda: self._gmail_connect_failed("Disconnected from Gmail; Google sending grant revoked.")),
                lambda message: self._on_ui(lambda: self._gmail_connect_failed(message)))
        except RuntimeError as error:
            self._gmail_connect_failed(str(error))

    def test_gmail_email(self, *_):
        if not self.model.store.notification_settings().email:
            self.notification_status.text = "Save a recipient email address first. Use your own address for the test."
            return
        alert = Alert("email","test",self.model.dataset.counter,self.model.dataset.scenario,2,12,0,
                      "SMA Stock Analyzer · Gmail test", "SIMULATED TEST · Gmail API email delivery is working.")
        self._authorize_delivery((alert,), test_email=True)

    def deliver_eod_alerts(self, *_):
        alerts = self.preview_eod_alerts()
        if not alerts:
            return
        self._delivery_controls(True)
        def after_permission(_allowed):
            # A denied phone permission must not prevent an enabled email channel.
            self._on_ui(lambda: self._authorize_delivery(alerts))
        try:
            if any(alert.channel=="phone" for alert in alerts):
                AndroidNotifier.request_permission(after_permission)
            else:
                self._authorize_delivery(alerts)
        except RuntimeError:
            self._authorize_delivery(alerts)

    def _authorize_delivery(self, alerts, test_email=False):
        self._delivery_controls(True)
        needs_email = any(alert.channel=="email" and
                          (test_email or not self.model.store.was_delivered(alert.key)) for alert in alerts)
        if not needs_email:
            self._run_delivery(alerts)
            return
        self.gmail_status.text = "Authorizing Gmail sending…"
        def success(token):
            self.gmail_sender.accept_access_token(token)
            self.gmail_status.text = f"Connected sender: {GMAIL_SENDER_ADDRESS}"
            self._run_delivery(alerts, self.gmail_sender, test_email)
        def failure(message):
            self.gmail_status.text = message
            # Keep phone delivery independent when Gmail permission is missing.
            self._run_delivery(alerts, test_email=test_email)
        try:
            self.gmail_authorizer.authorize(GMAIL_SENDER_ADDRESS,
                lambda token: self._on_ui(lambda: success(token)),
                lambda message: self._on_ui(lambda: failure(message)))
        except RuntimeError as error:
            failure(str(error))

    def _run_delivery(self, alerts, mailer=None, test_email=False):
        def work():
            if test_email:
                if mailer is None:
                    return ["No email sent. Connect Gmail using the Android build; see Gmail status above."]
                mailer.send(alerts[0],self.model.store.notification_settings().email)
                return ["Test email accepted by Gmail. Check the recipient inbox and sender Sent folder."]
            return deliver_alerts(self.model.store,alerts,mailer=mailer)
        future = self.executor.submit(work)
        future.add_done_callback(lambda completed: self._on_ui(lambda: self._finish_alert_delivery(completed)))

    def _finish_alert_delivery(self, future):
        self._delivery_controls(False)
        try:
            self.notification_status.text = "\n".join(future.result())
        except RuntimeError as error:
            self.notification_status.text = str(error)
        except Exception:
            self.notification_status.text = "Delivery could not be confirmed. Check Android permission, Gmail status and Sent before retrying."

    def _crossing_table(self, rows):
        table = GridLayout(cols=3, size_hint_y=None, row_default_height=dp(30),
                           row_force_default=True,spacing=dp(3))
        table.bind(minimum_height=table.setter("height"))
        for title in ("Session","Sim. close","SMA"):
            table.add_widget(Label(text=title,color=MUTED,font_size=sp(12)))
        for row in rows:
            for value in row:
                table.add_widget(Label(text=value,color=TEXT,font_size=sp(12)))
        return table

    def _refresh_table(self):
        if self.model.result is not self._table_result:
            self.visible_crossovers = 5
            self._table_result = self.model.result
        self.table_panel.clear_widgets()
        self.table_panel.add_widget(WrappedLabel(text="03  /  CROSSOVERS · SELECTED SMA",font_size=sp(11),bold=True,color=MUTED))
        self.crossing_count_label = WrappedLabel(
            text=(f"{self.model.result.crossing_count} upward crossings across all observable history"
                  if self.model.result else "Optimize to calculate upward crossings."),
            color=ACTIVE_COLOR,bold=True)
        self.table_panel.add_widget(self.crossing_count_label)
        rows = self.model.event_rows()
        self.rendered_crossover_rows = rows[:self.visible_crossovers]
        self.crossover_table = None
        self.more_crossings_button = None
        if not rows:
            self.table_panel.add_widget(WrappedLabel(text="No upward crossings for the selected SMA.",color=MUTED))
            return
        self.crossover_table = self._crossing_table(self.rendered_crossover_rows)
        self.table_panel.add_widget(self.crossover_table)
        footer = BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(8))
        footer.add_widget(WrappedLabel(text=f"Showing {len(self.rendered_crossover_rows)} of {len(rows)}",color=MUTED,font_size=sp(11)))
        if len(rows) > self.visible_crossovers:
            if self.visible_crossovers >= 35:
                self.more_crossings_button = LabButton(text="Show all",size_hint_x=None,width=dp(110))
            else:
                self.more_crossings_button = IconButton(kind="down")
            self.more_crossings_button.bind(on_release=self.show_more_crossings)
            footer.add_widget(self.more_crossings_button)
        self.table_panel.add_widget(footer)

    def show_more_crossings(self, *_):
        if self.visible_crossovers >= 35:
            self.full_table_panel.clear_widgets()
            data, result = self.model.dataset,self.model.result
            self.full_table_panel.add_widget(WrappedLabel(
                text=f"{data.counter} · {data.scenario} · SMA {result.period} · {result.crossing_count} upward crossings",bold=True))
            self.full_crossover_table = self._crossing_table(self.model.event_rows())
            self.full_table_panel.add_widget(self.full_crossover_table)
            self.saved_sheet.dismiss(animate=False)
            self.manager.current = "crossovers"
            self.full_crossovers_scroll.scroll_y = 1
        else:
            self.visible_crossovers = min(35,self.visible_crossovers+10)
            self._refresh_table()

    def close(self):
        self.closed = True
        self.gmail_sender.disconnect()
        self.gmail_authorizer.close()
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

    def on_pause(self):
        # Google consent can temporarily cover the Kivy activity.
        return True

    def on_stop(self):
        if hasattr(self, "screen"):
            self.screen.close()
