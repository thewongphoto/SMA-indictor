"""Portrait-first, offline Kivy application. Worker calculations never touch widgets."""
from concurrent.futures import ThreadPoolExecutor
import logging
import os
from pathlib import Path
import sqlite3
from dataclasses import replace

from kivy.config import Config
from kivy.utils import platform

# A portrait desktop window is a convenient stand-in for the eventual phone UI.
if platform != "android":
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
from kivy.uix.floatlayout import FloatLayout
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
from .model import AnalyzerModel, PlotLine
from .guide import INTRODUCTION, RECOVERY_HELP, RISK_HELP, COMPARISON_HELP, calculate_lesson
from .settings import ALLOW_CUSTOM_TARGET, SCENARIOS, TARGET_FREQUENCIES
from .storage import LineStore
from .viewport import available_timelines
from .widgets import (TimelineSelector, RoundedSelector, LegendItem, LegendSymbol,
                      IconButton, IconSymbol, RuleSwitch, SecurityMatchButton,
                      SecurityIdentity, SecurityIdentityButton, SavedSecurityGroup)
from .notifications import evaluate_eod, deliver_alerts, AndroidNotifier, Alert
from .android_window import AndroidWindow
from .backtest import compare_investments, period_sessions
from .securities import security_by_key, normalize_query

BG = (0.075, 0.122, 0.192, 1)
PANEL = (0.122, 0.188, 0.282, 1)
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


class EditingField(TextInput):
    """Keep focus through touch replay/IME layout; Done, Back or an action ends editing."""
    def __init__(self, **kwargs):
        kwargs.setdefault("unfocus_on_touch", False)
        kwargs.setdefault("write_tab", False)
        super().__init__(**kwargs)


class DeviceFrame(FloatLayout):
    """All pages and the sheet share the same measured safe/keyboard viewport."""
    def __init__(self, screen, **kwargs):
        super().__init__(**kwargs)
        self.screen = screen
        self.metrics = None
        screen.size_hint = (None, None)
        self.add_widget(screen)
        self.bind(pos=self._arrange, size=self._arrange)

    def apply_metrics(self, metrics):
        self.metrics = metrics
        self._arrange()

    def _arrange(self, *_):
        bounds = (self.metrics.content_bounds(*self.size) if self.metrics else
                  (0, 0, *self.size))
        x, y, width, height = bounds
        self.screen.pos = (self.x+x, self.y+y)
        self.screen.size = (width, height)
        self.screen.keep_editor_visible()


class AnalyzerScreen(FloatLayout):
    def __init__(self, model, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*BG)
            self._background = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._paint_background, size=self._paint_background)
        self.model = model
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sma")
        self.market_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="security")
        self.search_busy = False
        self.history_loading = False
        self._search_token = 0
        self._history_token = 0
        self._submitted_query = ""
        self._pending_security_key = None
        self._syncing_search = False
        self.search_results = ()
        self.security_match_buttons = []
        self.busy = False
        self.closed = False
        self._job = 0
        self._syncing_controls = False
        self._page_stack = ["library"]
        self._result_origin = "parameters"
        saved = model.store.list_all_lines()
        self.expanded_saved_securities = {saved[0].counter} if saved else set()
        self._guide_job = 0
        self.guide_busy = False
        self.guide_lesson = None
        self.delivery_busy = False
        self.manager = ScreenManager(transition=NoTransition(), pos_hint={"x": 0, "y": 0})
        self.add_widget(self.manager)
        self.pages = {}
        for name in ("library", "search", "parameters", "results", "crossovers", "settings", "guide"):
            page = Screen(name=name)
            self.pages[name] = page
            self.manager.add_widget(page)
        self.scroll, self.content = self._scrolling_page("results", chart=True, footer=True)
        self.parameter_scroll, self.parameter_content = self._scrolling_page("parameters")
        self.library_scroll, self.library_content = self._scrolling_page("library")
        self.search_scroll, self.search_content = self._scrolling_page("search")
        self.guide_scroll, self.guide_content = self._scrolling_page("guide", chart=True)
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

        self.search_panel = Panel()
        self.search_content.add_widget(self.search_panel)
        self.search_panel.add_widget(WrappedLabel(text="SEARCH SECURITY", color=MUTED, font_size=sp(10)))
        search_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.security_search = EditingField(multiline=False, hint_text="Ticker or company name",
            font_size=sp(14), padding=(dp(10),dp(12)), keyboard_suggestions=False,
            background_normal="", background_active="", background_color=(.12,.17,.23,1),
            foreground_color=TEXT, cursor_color=PRICE_COLOR)
        self.search_submit = LabButton(text="Submit", size_hint_x=None, width=dp(82))
        self.search_submit.bind(on_release=self.submit_security_search)
        search_row.add_widget(self.security_search)
        search_row.add_widget(self.search_submit)
        self.search_panel.add_widget(search_row)
        self.search_status = WrappedLabel(text="Search the preview catalogue by ticker or company name. All prices are simulated.",
                                          color=MUTED, font_size=sp(11))
        self.search_panel.add_widget(self.search_status)
        self.search_matches = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        self.search_matches.bind(minimum_height=self.search_matches.setter("height"))
        self.search_results_scroll = ScrollView(size_hint_y=None, height=0, do_scroll_x=False)
        self.search_results_scroll.add_widget(self.search_matches)
        self.search_matches.bind(height=lambda _,height:setattr(self.search_results_scroll,"height",min(dp(288),height)))
        self.search_panel.add_widget(self.search_results_scroll)

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

        self.counter = SecurityIdentityButton(text=model.dataset.counter, filled=True,
                                              logo_size=dp(24), padding=(dp(8),0))
        self.counter.bind(on_release=lambda _: self.focus_security_search())
        field("SELECTED SECURITY", self.counter)
        self.scenario = choice(model.dataset.scenario, SCENARIOS)
        self.scenario_cell = field("SCENARIO (FICTIONAL)", self.scenario)
        self.control_grid.remove_widget(self.scenario_cell)
        self.custom_toggle = LabButton(text="Custom  +")
        self.custom_toggle.bind(on_release=self.toggle_custom)
        self.custom_panel = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        self.custom_panel.bind(minimum_height=self.custom_panel.setter("height"))
        self.custom_panel.add_widget(self.scenario_cell)
        controls.add_widget(self.custom_toggle)
        target_row = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        target_row.bind(minimum_height=target_row.setter("height"))
        target_values = tuple(f"{n} / year" for n in TARGET_FREQUENCIES) + (("Custom",) if ALLOW_CUSTOM_TARGET else ())
        self.target = choice(f"{model.target_frequency} / year", target_values)
        target_row.add_widget(self.target)
        self.custom_target = EditingField(text="9", multiline=False, input_type="number",
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
        self.plot_title = SecurityIdentity(security_by_key(model.dataset.counter),
                                           height=dp(44), font_size=sp(15))
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
        plot_panel.add_widget(WrappedLabel(text="Drag one finger to inspect EOD prices. Pinch with two fingers to zoom in/out.", font_size=sp(11), color=MUTED))
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
        self.landing_saved_panel = Panel()
        self.library_intro = Panel()
        self.library_intro.add_widget(WrappedLabel(text=INTRODUCTION, bold=True, font_size=sp(20)))
        self.library_intro.add_widget(WrappedLabel(text="See how recovery signals and false crossings appear over three simulated years.", color=MUTED))
        self.guide_button = LabButton(text="See the guided example")
        self.guide_button.bind(on_release=self.show_guide)
        self.library_intro.add_widget(self.guide_button)
        self.new_analysis_button = LabButton(text="New analysis", primary=True)
        self.new_analysis_button.bind(on_release=self.show_search)
        self.library_archive_button = LabButton(text="Recently unsaved SMAs")
        self.library_archive_button.bind(on_release=self.open_unsaved_history)
        self.table_panel = Panel()
        self.content.add_widget(self.table_panel)
        self.settings_back_button = self._page_heading("settings","Notification settings")
        self.crossovers_back_button = self._page_heading("crossovers","All upward crossings")
        self.full_table_panel = Panel()
        self.full_crossovers_content.add_widget(self.full_table_panel)
        self._build_notification_settings()
        self.library_settings_button = self._page_heading("library", "My SMA library")
        self.library_settings_button.unbind(on_release=self.go_back)
        self.library_settings_button.kind = "settings"
        self.library_settings_button.bind(on_release=self.show_settings)
        self.search_back_button = self._page_heading("search", "Choose a security")
        self.parameters_back_button = self._page_heading("parameters", "Set your preference")
        self.guide_back_button = self._page_heading("guide", "Guided example")
        self._build_guide()
        for editor in self.editors:
            editor.bind(focus=self._editor_focus)
        self._editor_scroll_trigger = Clock.create_trigger(self._scroll_editor, .12)
        self.settings_scroll.bind(size=self.keep_editor_visible)
        self.content.add_widget(WrappedLabel(
            text="Research tool only. Matching a crossing frequency does not establish profitability. "
                 "All prices are simulated; 252 sessions represent one trading year.",
            color=MUTED, font_size=sp(11)))

        self.security_search.bind(text=self.on_security_query_edited, on_text_validate=self.submit_security_search)
        self.counter.bind(text=self.on_dataset_change)
        self.scenario.bind(text=self.on_dataset_change)
        self.target.bind(text=self.on_target_change)
        self.custom_target.bind(text=self.on_custom_target)
        self.scroll.bind(width=self._layout_for_width)
        self._layout_for_width()
        self.refresh()
        self.manager.current = "library"

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
            self.saved_menu_label = LabButton(text="Saved SMAs", halign="left")
            self.saved_menu_label.bind(on_release=self.toggle_saved_sheet)
            bar.add_widget(self.saved_menu_label)
            self.settings_button = IconButton(kind="settings")
            self.settings_button.bind(on_release=self.show_settings)
            bar.add_widget(self.settings_button)
            self.results_footer.add_widget(bar)
            self.results_feedback = WrappedLabel(text="",color=MUTED,font_size=sp(11))
            # Fixed top toolbar; no bottom tab bar in the library-first flow.
            self.results_toolbar = self.results_footer
            library = LabButton(text="Library", size_hint_x=None, width=dp(70))
            library.bind(on_release=self.show_library)
            bar.add_widget(library,index=len(bar.children))
            column.add_widget(self.results_toolbar,index=len(column.children))
        return scroll, content

    def _page_heading(self, page_name, title):
        # Keep Back reachable even at the bottom of a long event list/settings.
        row = BoxLayout(size_hint_y=None,height=dp(56),spacing=dp(8),padding=(dp(16),dp(6)))
        button = IconButton(kind="back")
        button.bind(on_release=self.go_back)
        row.add_widget(button)
        row.add_widget(WrappedLabel(text=title,bold=True,font_size=sp(18),pos_hint={"center_y":.5}))
        column = self.pages[page_name].children[0]
        column.add_widget(row,index=len(column.children))
        return button

    def _resize(self, *_):
        for scroll in (self.scroll,self.parameter_scroll,self.library_scroll,self.search_scroll,
                       self.guide_scroll,self.settings_scroll,self.full_crossovers_scroll):
            scroll.width = min(self.width, dp(1000))

    def show_library(self, *_):
        self._navigate("library")
        self._refresh_saved()
        self._reset_scroll(self.library_scroll)

    def show_search(self, *_):
        self._navigate("search")
        self._reset_scroll(self.search_scroll)

    @staticmethod
    def _reset_scroll(scroll):
        effect = scroll.effect_y
        if effect is not None:
            effect.velocity = 0
            effect.is_manual = False
            effect.trigger_velocity_update.cancel()
        scroll.scroll_y = 1
        if effect is not None:
            effect.value = effect.max

    def toggle_custom(self, *_):
        if self.custom_panel.parent is None:
            self.controls.add_widget(self.custom_panel)
            self.custom_toggle.text = "Custom  −"
        else:
            self.controls.remove_widget(self.custom_panel)
            self.custom_toggle.text = "Custom  +"

    def _build_guide(self):
        self.guide_content.add_widget(WrappedLabel(text=INTRODUCTION,bold=True,font_size=sp(22)))
        for text in (RECOVERY_HELP,RISK_HELP):
            self.guide_content.add_widget(WrappedLabel(text=text,color=MUTED))
        self.guide_target = choice("12 / year",("1 / year","6 / year","12 / year"))
        self.guide_target.bind(on_select=self._load_guide)
        self.guide_content.add_widget(WrappedLabel(text="Try a target upward crossing frequency"))
        self.guide_content.add_widget(self.guide_target)
        self.guide_status = WrappedLabel(text="",color=MUTED)
        self.guide_content.add_widget(self.guide_status)
        self.guide_chart = PriceChart(size_hint_y=None,height=dp(280))
        self.guide_scroll.chart = self.guide_chart
        self.guide_content.add_widget(self.guide_chart)
        self.guide_content.add_widget(WrappedLabel(text="3Y simulated history · turquoise close · amber SMA/plus crossings. Drag to inspect; pinch to zoom.",color=MUTED,font_size=sp(11)))
        self.guide_content.add_widget(WrappedLabel(text=COMPARISON_HELP,color=MUTED))
        self.guide_values = WrappedLabel(text="",bold=True)
        self.guide_content.add_widget(self.guide_values)
        self.guide_start_button = LabButton(text="Choose my own security",primary=True)
        self.guide_start_button.bind(on_release=self.show_search)
        self.guide_content.add_widget(self.guide_start_button)

    def show_guide(self, *_):
        self._navigate("guide")
        self._load_guide()

    def _load_guide(self, *_):
        self._guide_job += 1
        token = self._guide_job
        self.guide_busy = True
        self.guide_status.text = "Calculating the three-year example…"
        future = self.executor.submit(calculate_lesson,int(self.guide_target.text.split()[0]))
        future.add_done_callback(lambda done:Clock.schedule_once(lambda _:self._guide_complete(done,token),0))

    def _guide_complete(self, future, token):
        if self.closed or token != self._guide_job:
            return
        self.guide_busy = False
        try:
            lesson = self.guide_lesson = future.result()
            result,report = lesson.result,lesson.report
            self.guide_chart.update(lesson.dataset.prices,
                [PlotLine("guide",result.period,result.target_frequency,result.sma,True)],
                lesson.dataset.dates,(result.period,result.sma))
            self.guide_chart.set_timeline("3Y")
            self.guide_status.text = (f"SIMULATED DATA · 756 sessions · SMA {result.period} · "
                f"target {result.target_frequency}/yr · observed {result.actual_annual_frequency:.2f}/yr · "
                f"{len(report.crossings.indices)} buys per comparison")
            values = [f"a. Upward crossings: ${report.crossings.ending_value:,.2f}"]
            for key,title in (("dca","b. Equal periods"),("random","c. Most common random")):
                scenario = getattr(report,key)
                delta = scenario.difference_percent(report.crossings)
                difference = "N/A" if delta is None else f"{delta:+.2f}%"
                values.append(f"{title}: ${scenario.ending_value:,.2f} ({difference} vs a)")
            self.guide_values.text = "\n".join(values)
        except Exception:
            logging.exception("Guided example failed")
            self.guide_status.text = "Could not load the example. Open it again to retry."

    def show_parameters(self, *_):
        self._navigate("parameters")
        self._refresh_saved()
        # Stop residual momentum from a previous visit before restoring the top.
        # A resized/expanded saved library can otherwise move the search offscreen.
        effect = self.parameter_scroll.effect_y
        if effect is not None:
            effect.velocity = 0
            effect.is_manual = False
            effect.trigger_velocity_update.cancel()
        self.parameter_scroll.scroll_y = 1
        if effect is not None:
            effect.value = effect.max

    def show_results(self, *_):
        self._navigate("results")

    def show_settings(self, *_):
        self._navigate("settings")

    def _navigate(self, name):
        self._before_navigation(name)
        self.finish_editing()
        self.saved_sheet.dismiss(animate=False)
        if name == "results":
            self._page_stack = (["library","results"] if self._result_origin == "library"
                                else ["library","search","parameters","results"])
        elif name in self._page_stack:
            self._page_stack = self._page_stack[:self._page_stack.index(name)+1]
        else:
            self._page_stack.append(name)
        self.manager.current = name

    def _before_navigation(self, destination):
        """Back/Library must not be undone by an asynchronous completion."""
        current = self.manager.current
        if current == "search" and destination != "search":
            pending = self.search_busy or self.history_loading
            self._search_token += 1
            self._history_token += 1
            self.search_busy = self.history_loading = False
            self.search_submit.disabled = False
            self._set_busy(self.busy)
            if pending:
                self.search_status.text = "Selection cancelled. Submit or select a match again to retry."
        if current == "parameters" and destination != "parameters" and self.busy:
            self._job += 1
            self._set_busy(False)
        if current == "guide" and destination != "guide":
            self._guide_job += 1
            self.guide_busy = False

    def go_back(self, *_):
        self.finish_editing()
        self.saved_sheet.dismiss(animate=False)
        if len(self._page_stack) > 1:
            self._before_navigation(self._page_stack[-2])
            self._page_stack.pop()
            self.manager.current = self._page_stack[-1]
            if self.manager.current in ("parameters","library"):
                self._refresh_saved()

    @property
    def editors(self):
        return (self.security_search, self.custom_target, self.alert_session) + ((self.backtest_years,) if hasattr(self, "backtest_years") else ())

    def finish_editing(self):
        for editor in self.editors:
            editor.focus = False

    def handle_back(self):
        """Consume overlays/editing first, then pages; only Library may exit."""
        for name in ("history_popup", "validation_popup", "backtest_help_popup"):
            popup = getattr(self, name, None)
            if popup is not None and popup._is_open:
                popup.dismiss()
                return True
        if self.saved_sheet.is_open:
            self.saved_sheet.dismiss()
            return True
        if any(editor.focus for editor in self.editors):
            self.finish_editing()
            return True
        if len(self._page_stack) > 1:
            self.go_back()
            return True
        return False

    def _editor_focus(self, editor, focused):
        if focused:
            self.keep_editor_visible()

    def keep_editor_visible(self, *_):
        trigger = getattr(self, "_editor_scroll_trigger", None)
        if trigger is not None:
            trigger()

    def _scroll_editor(self, *_):
        for editor in self.editors:
            if editor.focus:
                scroll = (self.search_scroll if editor is self.security_search else
                          self.parameter_scroll if editor is self.custom_target else
                          self.scroll if editor is getattr(self, "backtest_years", None) else self.settings_scroll)
                scroll.scroll_to(editor, padding=dp(20), animate=False)
                break

    def toggle_saved_sheet(self, *_):
        if self.saved_sheet.is_open:
            self.saved_sheet.dismiss()
        else:
            self.saved_sheet.open()

    def _paint_background(self, *_):
        self._background.pos, self._background.size = self.pos, self.size

    def _layout_for_width(self, *_):
        """Stack narrow-phone controls so a logo leaves room for a whole name word."""
        wide = self.scroll.width >= dp(760)
        self.control_grid.cols = 3 if wide else 1
        for content in (self.content,self.parameter_content,self.library_content,self.search_content,
                        self.guide_content,self.settings_content,self.full_crossovers_content):
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

    def focus_security_search(self):
        self.show_search()
        self.security_search.focus = True
        self.security_search.select_all()
        self.search_scroll.scroll_to(self.search_panel, animate=False)

    def _clear_security_matches(self):
        self.search_results = ()
        self.security_match_buttons = []
        self.search_matches.clear_widgets()

    def on_security_query_edited(self, *_):
        if self._syncing_search:
            return
        # Editing invalidates old responses but never starts a provider request.
        self._search_token += 1
        self._history_token += 1
        self.search_busy = self.history_loading = False
        self.search_submit.disabled = False
        self._clear_security_matches()
        self.search_status.text = "Press Enter or Submit to search. Preview prices are simulated."
        self._set_busy(self.busy)

    def submit_security_search(self, *_):
        if self.manager.current != "search":
            self.show_search()
        try:
            query = normalize_query(self.security_search.text)
        except ValueError as error:
            self.search_status.text = str(error)
            return
        if not query:
            self.search_status.text = "Enter a ticker or company name, then press Enter or Submit."
            return
        if self.search_busy and query == self._submitted_query:
            return
        self.security_search.focus = False
        self._search_token += 1
        token = self._search_token
        self._submitted_query = query
        self.search_busy = True
        self.search_submit.disabled = True
        self._clear_security_matches()
        self.search_status.text = "Searching preview securities…"
        future = self.market_executor.submit(self.model.data_provider.search, query)
        future.add_done_callback(lambda done: Clock.schedule_once(lambda _: self._security_search_complete(done, token), 0))

    def _security_search_complete(self, future, token):
        if self.closed or token != self._search_token:
            return
        self.search_busy = False
        self.search_submit.disabled = False
        try:
            matches = tuple(future.result())
            self.search_results = matches
            for security in matches:
                button = SecurityMatchButton(security)
                button.disabled = self.busy
                button.bind(on_release=lambda _, item=security: self.select_security_match(item))
                self.security_match_buttons.append(button)
                self.search_matches.add_widget(button)
            self.search_status.text = (f"{len(matches)} preview matches. Select one to load simulated history."
                                       if matches else "No preview matches. Try a partial ticker or company name, such as Apple or DBS.")
        except Exception:
            self._clear_security_matches()
            self.search_status.text = "Search could not be completed. Press Submit to try again."

    def select_security_match(self, security):
        if self.busy or security not in self.search_results:
            return
        if self.history_loading and self._pending_security_key == security.key:
            return
        self.security_search.focus = False
        self._history_token += 1
        token = self._history_token
        self._pending_security_key = security.key
        self.history_loading = True
        scenario = self.scenario.text
        self._set_busy(False)
        self.search_status.text = f"Loading simulated history for {security.ticker}…"
        future = self.market_executor.submit(self.model.data_provider.historical_data, security, scenario)
        future.add_done_callback(lambda done: Clock.schedule_once(
            lambda _: self._security_history_complete(done, token, security, scenario), 0))

    def _security_history_complete(self, future, token, security, scenario):
        if self.closed or token != self._history_token:
            return
        self.history_loading = False
        self._set_busy(False)
        try:
            dataset = future.result()
            if dataset.counter != security.key or dataset.scenario != scenario or len(dataset.prices) < 4:
                raise ValueError("History does not match the selected security.")
            self.model.apply_dataset(dataset)
            self._job += 1
            self._syncing_controls = True
            try:
                self.counter.text = security.key
            finally:
                self._syncing_controls = False
            self._show_selected_security(security)
            self.show_parameters()
            self.refresh()
            self.message("Simulated history loaded. Press Optimize SMA to calculate a result.", quiet=True)
        except Exception:
            self.search_status.text = "Could not load history. Your previous security is unchanged; select a match to retry."

    def _show_selected_security(self, security):
        self._search_token += 1
        self.search_busy = False
        self.search_submit.disabled = False
        self._syncing_search = True
        try:
            self.security_search.text = security.ticker
        finally:
            self._syncing_search = False
        self._clear_security_matches()
        self.search_status.text = f"Selected {security.ticker} · {security.name}. Simulated history ready."

    def on_dataset_change(self, *_):
        if self._syncing_controls:
            return
        self._job += 1
        self._history_token += 1
        self.history_loading = False
        try:
            self.model.select_dataset(self.counter.text, self.scenario.text)
            self._show_selected_security(security_by_key(self.counter.text))
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
        if not self._syncing_controls:
            self._target_edited()

    def on_custom_target(self, *_):
        if self.target.text == "Custom" and not self._syncing_controls:
            self._target_edited()

    def _target_edited(self):
        self._job += 1
        self.model.viewing_saved = False
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
            widget.disabled = busy or self.history_loading
        for button in self.security_match_buttons:
            button.disabled = busy
        self.save_button.disabled = busy or self.model.result is None
        self.hide_button.disabled = busy or self.model.result is None

    def on_optimize(self, *_):
        if self.busy or self.history_loading:
            return
        self.show_parameters()
        self._result_origin = "parameters"
        try:
            self._read_target()
        except ValueError as error:
            self.message(str(error), True)
            return
        self._job += 1
        token = self._job
        self._calculation_job = token
        self._set_busy(True)
        self.message("Calculating all candidate periods across the full simulated history…")
        future = self.executor.submit(optimize_sma, self.model.dataset.prices, self.model.target_frequency)
        future.add_done_callback(lambda completed: Clock.schedule_once(
            lambda _dt: self._complete(completed, token), 0))

    def _complete(self, future, token):
        if self.closed:
            return
        if token != self._job:
            if token == getattr(self, "_calculation_job", None):
                self._set_busy(False)
            return
        self._set_busy(False)
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
                self.expanded_saved_securities.add(self.model.dataset.counter)
                self._refresh_saved()
                self.saved_sheet.open()
        except (ValueError, sqlite3.Error, OSError) as error:
            self.message(f"Could not save line: {error}. Check local storage permissions.", True)

    def on_active_visibility(self, *_):
        self.model.active_visible = not self.model.active_visible
        self.refresh()

    def on_saved_visibility(self, line, *_):
        try:
            current = line.visible
            active = (self.model.result is not None and line.period == self.model.result.period
                      and (line.counter, line.scenario) == (self.model.dataset.counter, self.model.dataset.scenario))
            if active:
                current = self.model.active_visible
            visible = not current
            self.model.store.set_visible(line.id, visible)
            if active:
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

    def on_view_saved(self, line, *_):
        if self.manager.current != "results":
            self._result_origin = "library" if self.manager.current == "library" else "parameters"
        if self.busy:
            return
        try:
            self._job += 1
            selected = self.model.view_saved_line(line.id)
            self._syncing_controls = True
            try:
                self.counter.text, self.scenario.text = selected.counter, selected.scenario
                self.custom_target.text = str(selected.target_frequency)
                self.target.text = (f"{selected.target_frequency} / year"
                                    if selected.target_frequency in TARGET_FREQUENCIES else "Custom")
            finally:
                self._syncing_controls = False
            self._history_token += 1
            self.history_loading = False
            self._show_selected_security(security_by_key(selected.counter))
            self.refresh()
            self.chart.set_timeline("1Y")
            self.show_results()
            self.scroll.scroll_y = 1
            self.message(f"Viewing saved SMA {selected.period} for {selected.counter} · {selected.scenario}.", quiet=True)
        except (ValueError, sqlite3.Error, OSError) as error:
            self.message(f"Could not open saved SMA: {error}", True)

    def refresh(self):
        self.last_alerts = ()
        self.alert_preview.text = "No current preview. Choose a session and press Preview EOD alerts."
        data = self.model.dataset
        self.alert_session_label.text = f"Test an end-of-day session (1–{len(data.prices)})"
        self.plot_title.set_security(security_by_key(data.counter))
        lines = self.model.plot_lines()
        self.chart.update(data.prices, lines, data.dates,
                          (self.model.result.period, self.model.result.sma) if self.model.result else None)
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
        self.optimal_caption.text = "SAVED SMA" if self.model.viewing_saved else "OPTIMAL SMA"
        self.hide_button.text = "Hide SMA" if self.model.active_visible else "Show SMA"
        result = self.model.result
        self.explanation.text = (
            f"Based on {result.comparisons} usable comparisons "
            f"({result.usable_years:.2f} trading years) from {result.history_sessions} sessions. "
            f"Target difference: {float(result.frequency_error):.2f}/yr. " +
            ("Viewing the exact saved period. " if self.model.viewing_saved else
             f"SMA search: 2–{maximum_sma_period(result.history_sessions)}. ") +
            "Warm-up and gaps are excluded. "
            + ("Saved parameters have not been re-optimized." if self.model.viewing_saved else
               "Ties choose the shorter SMA. " +
               ("Closest eligible result; target not matched exactly." if result.frequency_error else "Target matched."))
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
        self.plot_subtitle.text = f"SIMULATED DATA · {len(data.prices)} sessions · fictional price units\nCrossing markers estimate daily-line intersections."
        if data.prices:
            start, end = self.chart.view_range
            self.plot_subtitle.text += f"\n{self.chart.timeline} view · sessions {start + 1}–{end + 1}"

    def _refresh_saved(self):
        self.saved_rows = self._populate_saved_panel(self.saved_panel, self.model.store.list_all_lines())
        self.landing_saved_rows = self._populate_saved_panel(
            self.landing_saved_panel, self.model.store.list_all_lines(), landing=True)
        self.library_content.clear_widgets()
        self.library_state = "populated" if self.model.store.list_all_lines() else "empty"
        widgets = ([self.new_analysis_button,self.landing_saved_panel,self.library_intro] if self.library_state == "populated"
                   else [self.library_intro,self.new_analysis_button,self.library_archive_button])
        for widget in widgets:
            self.library_content.add_widget(widget)

    def _populate_saved_panel(self, panel, saved, landing=False):
        panel.clear_widgets()
        header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        header.add_widget(WrappedLabel(text="02  /  SAVED SMA LINES", font_size=sp(11), bold=True, color=MUTED))
        history = IconButton(kind="history")
        history.bind(on_release=self.open_unsaved_history)
        if landing:
            self.landing_history_button = history
        else:
            self.history_button = history
        header.add_widget(history)
        panel.add_widget(header)
        rows = {}
        if not saved:
            panel.add_widget(WrappedLabel(text="No saved SMAs yet. Optimize, then tap the heart.", color=MUTED))
        buttons, groups = {}, {}
        for security in sorted({line.counter for line in saved}):
            entries = [line for line in saved if line.counter == security]
            group = SavedSecurityGroup(expanded=security in self.expanded_saved_securities)
            heading = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
            name = SecurityIdentityButton(text=security, show_ticker=True)
            arrow = IconButton(kind="up" if security in self.expanded_saved_securities else "down")
            for button in (name, arrow):
                button.bind(on_release=lambda _, counter=security: self.toggle_saved_security(counter))
                heading.add_widget(button)
            group.add_widget(heading)
            body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10),
                             padding=(dp(4),dp(4),dp(4),dp(6)))
            body.bind(minimum_height=body.setter("height"))
            for line in entries:
                rows[line.id] = self._add_saved_row(body, line)
            if security in self.expanded_saved_securities:
                group.add_widget(body)
            panel.add_widget(group)
            buttons[security] = arrow
            groups[security] = dict(group=group, body=body, name=name)
        if landing:
            self.landing_security_buttons, self.landing_security_groups = buttons, groups
        else:
            self.saved_security_buttons, self.saved_security_groups = buttons, groups
        return rows

    def toggle_saved_security(self, security):
        if security in self.expanded_saved_securities:
            self.expanded_saved_securities.remove(security)
        else:
            self.expanded_saved_securities.add(security)
        self._refresh_saved()

    def _add_saved_row(self, panel, line):
        label = f"{line.scenario} · SMA {line.period} · target {line.target_frequency}/yr"
        if len(self.model.dataset.prices) >= 4 and line.period > maximum_sma_period(len(self.model.dataset.prices)):
            label += " · saved previously; outside current search limit"
        title = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(5))
        active = (self.model.result is not None and self.model.result.period == line.period
                  and (line.counter, line.scenario) == (self.model.dataset.counter, self.model.dataset.scenario))
        swatch = LegendSymbol(self.chart.period_color(line.period, active))
        title.add_widget(swatch)
        title_label = Button(text=label, color=TEXT, font_size=sp(13), halign="left",
                             background_normal="", background_down="", background_color=(0,0,0,0))
        title_label.bind(width=lambda widget, width: setattr(widget, "text_size", (width, None)))
        title_label.bind(texture_size=lambda _, size: setattr(title, "height", max(dp(44), size[1]+dp(8))))
        title_label.bind(on_release=lambda _: self.on_view_saved(line))
        title.add_widget(title_label)
        panel.add_widget(title)
        channels = GridLayout(cols=1, size_hint_y=None, spacing=dp(6))
        channels.bind(minimum_height=channels.setter("height"))
        push = LabButton(text="Push notifications " + ("On" if line.push_enabled else "Off"))
        for button, enabled in ((push, line.push_enabled),):
            button.font_size = sp(11)
            if enabled:
                button.fill = (0.12,0.35,0.32,1)
                button._draw()
            channels.add_widget(button)
        push.bind(on_release=lambda _: self.on_line_alert(line, "phone"))
        panel.add_widget(channels)
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        actions.add_widget(Label())
        view = LabButton(text="View", size_hint_x=None, width=dp(64))
        view.bind(on_release=lambda _: self.on_view_saved(line))
        visible = self.model.active_visible if active else line.visible
        toggle = LabButton(text="Hide" if visible else "Show", size_hint_x=None, width=dp(64))
        toggle.bind(on_release=lambda _: self.on_saved_visibility(line))
        heart = IconButton(kind="heart", selected=True)
        heart.bind(on_release=lambda _: self.on_delete(line))
        for button in (view, toggle, heart):
            actions.add_widget(button)
        panel.add_widget(actions)
        return dict(push=push, view=view, hide=toggle, heart=heart, swatch=swatch, title=title_label)

    def on_line_alert(self, line, channel):
        if channel != "phone":
            return
        enabled = line.push_enabled
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
        self.history_identities = {}
        for line in self.model.store.recent_unsaved():
            entry = SavedSecurityGroup()
            identity = SecurityIdentity(security_by_key(line.counter), logo_size=dp(20),
                                         height=dp(32), font_size=sp(12))
            entry.add_widget(identity)
            entry.add_widget(WrappedLabel(text=f"{line.scenario} · SMA {line.period} · target {line.target_frequency}/yr",
                                           color=MUTED, font_size=sp(12)))
            restore = LabButton(text="Restore saved line")
            restore.bind(on_release=lambda _, entry=line: self.restore_unsaved(entry))
            entry.add_widget(restore)
            entries.add_widget(entry)
            self.history_restore_buttons[line.id] = restore
            self.history_identities[line.id] = identity
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
        self.settings_panel.add_widget(WrappedLabel(text="SIMULATED DATA · Manual EOD tests. Preview sends nothing; Send enabled alerts posts phone notifications.",color=MUTED,font_size=sp(11)))
        settings = self.model.store.notification_settings()
        self.notification_switches = {}
        descriptions = {
            "buy": ("Buy signal: Upward crossing detected", "Triggers an alert when the end-of-day price crosses above a SMA."),
            "monitor": ("Impending buy signal", "Triggers an alert once per EOD session when the close is strictly below a SMA."),
        }
        for channel, icon, title in (("phone","phone","Phone notifications"),):
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
        self.notification_status = WrappedLabel(text="Preview sends nothing. Send enabled alerts posts selected phone notifications.",color=MUTED,font_size=sp(11))
        self.settings_panel.add_widget(self.notification_status)
        self.alert_session_label = WrappedLabel(text="Test an end-of-day session (1–1260)",color=MUTED,font_size=sp(11))
        self.settings_panel.add_widget(self.alert_session_label)
        test_row = BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(8))
        self.alert_session = EditingField(text="1260",multiline=False,input_filter="int",input_type="number",font_size=sp(13),
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

    def preview_eod_alerts(self, *_):
        self.alert_session.focus = False
        try:
            self.notification_status.text = "Preview only · no notification was sent."
            try:
                session = int(self.alert_session.text)
            except ValueError:
                raise ValueError("Enter a valid EOD session number, such as 1260.") from None
            # Preserve legacy preferences in SQLite, but never expose or dispatch
            # their email channel in this phone-only application.
            settings = replace(self.model.store.notification_settings(), email_buy=False, email_monitor=False)
            self.last_alerts = tuple(alert for line in self.model.saved_lines()
                                    for alert in evaluate_eod(self.model.dataset.prices,line,settings,session)
                                    if alert.channel == "phone")
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
        self.eod_deliver_button.disabled = busy
        self.phone_test_button.disabled = busy

    def deliver_eod_alerts(self, *_):
        alerts = self.preview_eod_alerts()
        if not alerts:
            return
        self._delivery_controls(True)
        def after_permission(allowed):
            def continue_delivery():
                if allowed:
                    self._run_delivery(alerts)
                else:
                    self._delivery_controls(False)
                    self.notification_status.text = "Notification permission denied. Enable it in Android Settings to send alerts."
            self._on_ui(continue_delivery)
        try:
            AndroidNotifier.request_permission(after_permission)
        except RuntimeError:
            self._run_delivery(alerts)

    def _run_delivery(self, alerts):
        # Keep this boundary phone-only even if called with legacy alert objects.
        phone_alerts = tuple(alert for alert in alerts if alert.channel == "phone")
        future = self.executor.submit(lambda: deliver_alerts(self.model.store, phone_alerts))
        future.add_done_callback(lambda completed: self._on_ui(lambda: self._finish_alert_delivery(completed)))

    def _finish_alert_delivery(self, future):
        self._delivery_controls(False)
        try:
            self.notification_status.text = "\n".join(future.result())
        except RuntimeError as error:
            self.notification_status.text = str(error)
        except Exception:
            self.notification_status.text = "Delivery could not be confirmed. Check Android notification permission and try again."

    def _crossing_table(self, rows):
        table = GridLayout(cols=3, size_hint_y=None, row_default_height=dp(30),
                           row_force_default=True,spacing=dp(3))
        table.bind(minimum_height=table.setter("height"))
        for title in ("Session","Crossing price","SMA at cross"):
            table.add_widget(Label(text=title,color=MUTED,font_size=sp(12)))
        for row in rows:
            for value in row:
                table.add_widget(Label(text=value,color=TEXT,font_size=sp(12)))
        return table

    def _refresh_table(self):
        # Keep the controls alive: refreshing after a save/hide must retain the period.
        if not hasattr(self, "backtest_period"):
            self.table_panel.add_widget(WrappedLabel(text="03  /  BACKTESTING · SELECTED SMA", font_size=sp(11), color=MUTED))
            self.backtest_header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
            self.backtest_heading = WrappedLabel(text="If you invested $100 for the past:", bold=True, font_size=sp(14))
            self.backtest_heading.pos_hint = {"center_y": .5}
            self.backtest_header.add_widget(self.backtest_heading)
            self.backtest_period = TimelineSelector(values=("1Y", "3Y", "5Y", "Max", "Custom"))
            self.backtest_period.width = dp(90)
            self.backtest_period.pos_hint = {"center_y": .5}
            self.backtest_header.add_widget(self.backtest_period)
            self.backtest_heading.bind(height=lambda _, height: setattr(self.backtest_header, "height", max(dp(48), height)))
            self.table_panel.add_widget(self.backtest_header)
            self.backtest_custom_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            self.backtest_custom_row.add_widget(WrappedLabel(text="Custom years"))
            self.backtest_years = EditingField(text="2", multiline=False, input_type="number", size_hint_y=None, height=dp(44))
            self.backtest_custom_row.add_widget(self.backtest_years)
            self.backtest_custom_row.add_widget(LabButton(text="Apply", on_release=self._refresh_backtest))
            self.backtest_custom_holder = BoxLayout(orientation="vertical", size_hint_y=None, height=0)
            self.table_panel.add_widget(self.backtest_custom_holder)
            self.backtest_details = WrappedLabel(color=MUTED, font_size=sp(11))
            self.table_panel.add_widget(self.backtest_details)
            self.backtest_values = {}
            self.backtest_differences = {}
            self.backtest_captions = {}
            self.backtest_info_buttons = {}
            for key in ("crossings", "dca", "random"):
                row = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
                row.bind(minimum_height=row.setter("height"))
                caption_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(2))
                caption = WrappedLabel(text="", bold=True)
                caption.pos_hint = {"center_y": .5}
                caption.bind(height=lambda _, height, box=caption_row: setattr(box, "height", max(dp(44), height)))
                caption_row.add_widget(caption)
                self.backtest_captions[key] = caption
                if key != "crossings":
                    info = IconButton(kind="info")
                    info.pos_hint = {"center_y": .5}
                    info.bind(on_release=lambda _, scenario=key: self.show_backtest_help(scenario))
                    caption_row.add_widget(info)
                    self.backtest_info_buttons[key] = info
                row.add_widget(caption_row)
                row.add_widget(WrappedLabel(text="Value of total investment", halign="right", font_size=sp(11), color=MUTED))
                value_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(4))
                value_row.add_widget(Label())
                value = Label(text="—", size_hint_x=None, bold=True, color=PRICE_COLOR, font_size=sp(17))
                value.bind(texture_size=lambda widget, size: setattr(widget, "width", size[0]+dp(2)))
                value_row.add_widget(value)
                if key != "crossings":
                    difference = Label(text="", size_hint_x=None, font_size=sp(11), color=MUTED)
                    difference.bind(texture_size=lambda widget, size: setattr(widget, "width", size[0]+dp(2)))
                    value_row.add_widget(difference)
                    self.backtest_differences[key] = difference
                row.add_widget(value_row)
                self.backtest_values[key] = value
                self.table_panel.add_widget(row)
            self.backtest_note = WrappedLabel(text="", color=MUTED, font_size=sp(12))
            self.table_panel.add_widget(self.backtest_note)
            self.crossing_details_button = LabButton(text="View all upward crossings")
            self.crossing_details_button.bind(on_release=self.show_more_crossings)
            self.table_panel.add_widget(self.crossing_details_button)
            self.backtest_period.bind(on_select=self._refresh_backtest)
            self.backtest_years.bind(on_text_validate=self._refresh_backtest, focus=self._editor_focus)
        self._refresh_backtest()

    def _refresh_backtest(self, *_):
        custom = self.backtest_period.text == "Custom"
        if custom and self.backtest_custom_row.parent is None:
            self.backtest_custom_holder.add_widget(self.backtest_custom_row)
        elif not custom and self.backtest_custom_row.parent is not None:
            self.backtest_custom_holder.remove_widget(self.backtest_custom_row)
            self.backtest_years.focus = False
        self.backtest_custom_holder.height = dp(44) if custom else 0
        self.backtest_report = None
        self.crossing_details_button.disabled = self.model.result is None
        for value in self.backtest_values.values():
            value.text = "—"
        for difference in self.backtest_differences.values():
            difference.text = ""
        if self.model.result is None:
            self.backtest_details.text = "Optimize or view a saved SMA to compare investments."
            self.backtest_note.text = ""
            self._set_backtest_captions("—")
            return
        try:
            data, result = self.model.dataset, self.model.result
            sessions = period_sessions(self.backtest_period.text, self.backtest_years.text, len(data.prices))
            report = compare_investments(data.prices, result.sma, result.events, sessions)
            self.backtest_report = report
            count = len(report.crossings.indices)
            self._set_backtest_captions(count)
            self.backtest_details.text = (f"Simulated dates: {data.dates[report.start]} - {data.dates[report.end]}\n"
                "Percentages compare ending values with scenario a.")
            self.backtest_note.text = (
                f"Scenario a's moving average strategy outperforms {report.outperformance_percent:.1f}% of all 500 random buy scenarios."
                if report.outperformance_percent is not None else
                "Scenario a's moving average strategy outperformance is N/A: no upward crossings in this period.")
            for key, value in self.backtest_values.items():
                scenario = getattr(report, key)
                value.text = f"${scenario.ending_value:,.2f}"
                if key in self.backtest_differences:
                    percent = scenario.difference_percent(report.crossings)
                    self.backtest_differences[key].text = ("(N/A vs a)" if percent is None
                        else f"({percent:+.2f}% vs a)")
        except ValueError as error:
            self.backtest_details.text = str(error)
            self.backtest_note.text = ""
            self._set_backtest_captions("—")

    def _set_backtest_captions(self, count):
        self.backtest_captions["crossings"].text = f"a. at {count} upward crossings."
        self.backtest_captions["dca"].text = f"b. at {count} equal periods."
        self.backtest_captions["random"].text = f"c. At {count} random points (most common scenario)."

    def show_backtest_help(self, scenario):
        if scenario == "dca":
            text = ("This scenario simulates the popular dollar cost averaging strategy. "
                    "It invests $100 at the EOD price at the start of each of N equal periods, "
                    "including the start of the chosen period when N is 1.")
        else:
            text = ("This scenario assumes the most common average price of 500 different scenarios "
                    "of investing N times in the chosen period. Each scenario uses a different random seed "
                    "and N distinct EOD purchase dates. Average purchase prices are rounded to the nearest dollar; "
                    "the most frequent dollar value defines the most common group. The displayed ending value "
                    "uses an actual sample closest to that dollar value, with $100 invested at each purchase. "
                    "The outperformance percentage counts random samples whose arithmetic average purchase price "
                    "is strictly higher than scenario a's average crossing price; ties are excluded.")
            report = self.backtest_report
            if report is not None and report.random_mode is not None:
                mode = report.random_mode
                text += f" Current mode: ${mode.rounded_price:,.0f} ({mode.frequency} of 500 samples)."
        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(12))
        scroll = ScrollView()
        label = WrappedLabel(text=text, font_size=sp(14))
        scroll.add_widget(label)
        content.add_widget(scroll)
        close = LabButton(text="Close")
        content.add_widget(close)
        self.backtest_help_popup = Popup(title="Dollar cost averaging" if scenario == "dca" else "Most common random scenario",
                                         content=content, size_hint=(.92, .6))
        close.bind(on_release=self.backtest_help_popup.dismiss)
        self.backtest_help_popup.open()

    def show_more_crossings(self, *_):
        if self.model.result is None:
            return
        self.full_table_panel.clear_widgets()
        data, result = self.model.dataset, self.model.result
        self.full_table_panel.add_widget(WrappedLabel(
            text=f"{data.counter} · {data.scenario} · SMA {result.period} · {result.crossing_count} upward crossings", bold=True))
        self.full_crossover_table = self._crossing_table(self.model.event_rows())
        self.full_table_panel.add_widget(self.full_crossover_table)
        self._navigate("crossovers")
        self.full_crossovers_scroll.scroll_y = 1

    def close(self):
        self.closed = True
        self._editor_scroll_trigger.cancel()
        self.finish_editing()
        self._search_token += 1
        self._history_token += 1
        self.market_executor.shutdown(wait=False, cancel_futures=True)
        self.executor.shutdown(wait=False, cancel_futures=True)


class SMAStockAnalyzerApp(App):
    title = "SMA Stock Analyzer"

    def build(self):
        Window.clearcolor = BG
        if platform != "android":
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
        # SDL2 reports keyboard_height as zero on Android: use measured native
        # surface/inset geometry instead of Kivy's unsupported resize mode.
        Window.softinput_mode = ""
        self.device_frame = DeviceFrame(self.screen)
        self.android_window = AndroidWindow()
        Window.bind(on_keyboard=self._on_keyboard)
        if platform == "android":
            try:
                self.android_window.start(lambda metrics: Clock.schedule_once(
                    lambda _: self.device_frame.apply_metrics(metrics) if not self.screen.closed else None, 0))
            except Exception:
                logging.exception("Android window metrics could not be installed")
        return self.device_frame

    def _on_keyboard(self, _window, key, *_):
        if key == 27 and hasattr(self, "screen"):
            return self.screen.handle_back()
        return False

    def on_pause(self):
        # Google consent can temporarily cover the Kivy activity.
        return True

    def on_stop(self):
        Window.unbind(on_keyboard=self._on_keyboard)
        if hasattr(self, "android_window"):
            self.android_window.stop()
        if hasattr(self, "screen"):
            self.screen.close()
