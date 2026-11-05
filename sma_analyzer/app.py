"""Portrait-first, offline Kivy application. Worker calculations never touch widgets."""
from concurrent.futures import Future, ThreadPoolExecutor
import logging
import os
from pathlib import Path
import sqlite3
from dataclasses import replace
from datetime import datetime
import math
from threading import Event

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
from .widgets import PreferenceReveal
from .notifications import evaluate_eod, evaluate_dataset_eod, deliver_alerts, AndroidNotifier, Alert
from .android_window import AndroidWindow
from .backtest import compare_investments, period_sessions
from .securities import security_by_key, normalize_query
from .version import APP_VERSION
from .presentation import display_text
from .palette import line_color as saved_color

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


class ScreenPopup(Popup):
    """Center within the measured safe/keyboard viewport rather than Window."""
    def __init__(self,owner,**kwargs):
        self.owner=owner
        super().__init__(**kwargs)

    def _align_center(self,*_):
        if self._is_open:
            self.center=self.owner.center

    def open(self,*args,**kwargs):
        super().open(*args,**kwargs)
        self._align_center()


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
        self.market_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="security")
        self._cancel_optimization = Event()
        self.yahoo_enabled = hasattr(model.data_provider, "cache")
        self.source_warning = WrappedLabel(text="", color=ERROR, font_size=sp(12))
        self._source_check_busy = False
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
        self.expanded_saved_securities = set()
        self.page_settings_buttons = {}
        self.page_titles = {}
        self.builder_selected = False
        self._guide_job = 0
        self.guide_busy = False
        self.guide_lesson = None
        self.delivery_busy = False
        self.manager = ScreenManager(transition=NoTransition(), pos_hint={"x": 0, "y": 0})
        self.add_widget(self.manager)
        self.pages = {}
        for name in ("library", "search", "results", "crossovers", "settings", "guide"):
            page = Screen(name=name)
            self.pages[name] = page
            self.manager.add_widget(page)
        self.scroll, self.content = self._scrolling_page("results", chart=True, footer=True)
        self.library_scroll, self.library_content = self._scrolling_page("library")
        self.search_scroll, self.search_content = self._scrolling_page("search")
        self.parameter_scroll,self.parameter_content=self.search_scroll,self.search_content
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
        if not self.yahoo_enabled:
            self.parameter_content.add_widget(header)
        header.add_widget(WrappedLabel(text="DAILY CLOSING PRICES" if self.yahoo_enabled else "OFFLINE EDUCATIONAL EXAMPLE", color=MUTED,
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
        self.search_status = WrappedLabel(text="Search the example catalogue by ticker or company name.",
                                          color=MUTED, font_size=sp(11))
        self.search_panel.add_widget(self.search_status)
        if self.yahoo_enabled:
            self.search_status.text = "Search US/SG stocks and ETFs. Enter or Submit searches; selecting a match loads daily history."
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
        if not self.yahoo_enabled:
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
        self.target_cell=field("TARGET CROSSINGS", target_row)
        self.optimize_button = LabButton(text="Optimize SMA", primary=True)
        self.optimize_button.bind(on_release=self.on_optimize)
        self.optimize_cell = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(65))
        self.optimize_cell.add_widget(Label())
        self.optimize_cell.add_widget(self.optimize_button)
        self.control_grid.add_widget(self.optimize_cell)
        self.control_grid.remove_widget(self.target_cell)
        self.control_grid.remove_widget(self.optimize_cell)
        self.preference_body=BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(12))
        self.preference_body.bind(minimum_height=self.preference_body.setter("height"))
        self.preference_body.add_widget(self.target_cell)
        self.preference_body.add_widget(self.optimize_cell)
        self.preference_reveal=PreferenceReveal(self.preference_body)
        controls.add_widget(self.preference_reveal)
        self.status = WrappedLabel(text="Choose a scenario, then press Optimize SMA.", color=MUTED)

        self.card_values = {}
        self.optimal_panel = Panel()
        self.optimal_value = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(3))
        self.optimal_value.bind(minimum_height=self.optimal_value.setter("height"))
        self.optimal_caption = WrappedLabel(text="OPTIMAL SMA", color=MUTED, font_size=sp(12))
        self.optimal_value.add_widget(self.optimal_caption)
        self.card_values["period"] = WrappedLabel(text="—", bold=True, font_size=sp(26), color=ACTIVE_COLOR)
        self.line_name_row=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(6))
        self.card_values["period"].pos_hint={"center_y":.5}
        self.card_values["period"].bind(height=lambda _,height:setattr(self.line_name_row,"height",max(dp(48),height)))
        self.line_name_row.add_widget(self.card_values["period"])
        self.rename_button=IconButton(kind="edit",pos_hint={"center_y":.5})
        self.rename_button.bind(on_release=self.show_rename_line)
        self.selected_target_badge=WrappedLabel(text="",size_hint_x=None,width=dp(104),
                                              font_size=sp(12),color=MUTED,halign="right",pos_hint={"center_y":.5})
        self.line_name_row.add_widget(self.selected_target_badge)
        self.optimal_value.add_widget(self.line_name_row)
        self.named_period_caption=WrappedLabel(text="",color=MUTED,font_size=sp(11))
        self.optimal_value.add_widget(self.named_period_caption)
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
        plot_panel.add_widget(WrappedLabel(text="Drag one finger to inspect "
            + ("adjusted daily prices." if self.yahoo_enabled else "EOD prices.")
            + " Pinch with two fingers to zoom in/out.",font_size=sp(11),color=MUTED))
        legend_holder = AnchorLayout(size_hint_y=None, height=dp(24))
        self.legend = StackLayout(size_hint=(None, None), spacing=(dp(12), dp(2)))
        self.legend.bind(minimum_height=self.legend.setter("height"))
        self.legend.bind(height=lambda _, height: setattr(legend_holder, "height", height))
        legend_holder.add_widget(self.legend)
        plot_panel.add_widget(legend_holder)

        def center_legend(*_):
            for item in self.legend.children:
                item.max_width=legend_holder.width
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
        self.landing_saved_panel = Panel()
        self.library_intro = Panel()
        self.library_intro.add_widget(WrappedLabel(text=INTRODUCTION, bold=True, font_size=sp(20)))
        self.library_intro.add_widget(WrappedLabel(text="See how recovery signals and false crossings appear on "
            + ("actual daily prices." if self.yahoo_enabled else "an educational price example."), color=MUTED))
        self.guide_button = LabButton(text="See the guided example")
        self.guide_button.bind(on_release=self.show_guide)
        self.library_intro.add_widget(self.guide_button)
        self.new_analysis_button = LabButton(text="New analysis", primary=True)
        self.new_analysis_button.bind(on_release=self.show_search)
        self.library_archive_button = LabButton(text="Recently unsaved SMAs")
        self.library_archive_button.bind(on_release=self.open_unsaved_history)
        self.table_panel = Panel()
        self.content.add_widget(self.table_panel)
        self.settings_back_button = self._page_heading("settings","Settings" if self.yahoo_enabled else "Notification settings")
        self.crossovers_back_button = self._page_heading("crossovers","All upward crossings")
        self.full_table_panel = Panel()
        self.full_crossovers_content.add_widget(self.full_table_panel)
        if self.yahoo_enabled:
            self._build_api_settings()
        self._build_notification_settings()
        self.library_settings_button = self._page_heading("library", "My SMA library")
        self.search_back_button = self._page_heading("search", "Choose a security")
        self.parameters_back_button = self.search_back_button
        self.guide_back_button = self._page_heading("guide", "Guided example")
        self._build_guide()
        for editor in self.editors:
            editor.bind(focus=self._editor_focus)
        self._editor_scroll_trigger = Clock.create_trigger(self._scroll_editor, .12)
        self.settings_scroll.bind(size=self.keep_editor_visible)
        self.content.add_widget(WrappedLabel(
            text="Research tool only. Matching a crossing frequency does not establish profitability. "
                 + ("Comparisons use dividend/split-adjusted prices and estimated crossing fills. Fees, taxes and currency movements are excluded. "
                  "Displayed market prices are historical." if self.yahoo_enabled else
                  "Educational example only; 252 sessions represent one trading year."),
            color=MUTED, font_size=sp(11)))

        self.security_search.bind(text=self.on_security_query_edited, on_text_validate=self.submit_security_search)
        self.counter.bind(text=self.on_dataset_change)
        self.scenario.bind(text=self.on_dataset_change)
        self.target.bind(text=self.on_target_change)
        self.custom_target.bind(text=self.on_custom_target)
        self.scroll.bind(width=self._layout_for_width)
        self._layout_for_width()
        self.refresh()
        self._builder_stage(False)
        self.manager.current = "library"
        if self.yahoo_enabled:
            Clock.schedule_once(lambda _: self.check_yahoo_source(), 0)
            Clock.schedule_once(lambda _: self.sync_notification_schedule(), .2)

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
            self.saved_menu_label = LabButton(text="Saved SMAs", halign="left")
            self.saved_menu_label.bind(on_release=self.toggle_saved_sheet)
            bar.add_widget(self.saved_menu_label)
            self.settings_button = IconButton(kind="settings")
            self.page_settings_buttons["results"] = self.settings_button
            self.settings_button.bind(on_release=self.show_settings)
            bar.add_widget(self.settings_button)
            self.results_footer.add_widget(bar)
            self.results_feedback = WrappedLabel(text="",color=MUTED,font_size=sp(11))
            # Fixed top toolbar; no bottom tab bar in the library-first flow.
            self.results_toolbar = self.results_footer
            self.new_security_button = IconButton(kind="search_add")
            self.new_security_button.bind(on_release=self.show_search)
            bar.add_widget(self.new_security_button,index=len(bar.children))
            column.add_widget(self.results_toolbar,index=len(column.children))
        return scroll, content

    def _page_heading(self, page_name, title):
        # Keep Back reachable even at the bottom of a long event list/settings.
        row = BoxLayout(size_hint_y=None,height=dp(56),spacing=dp(8),padding=(dp(16),dp(6)))
        button = IconButton(kind="back")
        button.bind(on_release=self.go_back)
        if page_name != "library":
            row.add_widget(button)
        heading=WrappedLabel(text=title,bold=True,font_size=sp(18),pos_hint={"center_y":.5})
        self.page_titles[page_name]=heading
        row.add_widget(heading)
        settings = IconButton(kind="settings")
        settings.bind(on_release=self.show_settings)
        row.add_widget(settings)
        self.page_settings_buttons[page_name] = settings
        column = self.pages[page_name].children[0]
        column.add_widget(row,index=len(column.children))
        return settings if page_name=="library" else button

    def _resize(self, *_):
        for scroll in (self.scroll,self.parameter_scroll,self.library_scroll,self.search_scroll,
                       self.guide_scroll,self.settings_scroll,self.full_crossovers_scroll):
            scroll.width = min(self.width, dp(1000))

    def show_library(self, *_):
        self._navigate("library")
        self._refresh_saved()
        self._reset_scroll(self.library_scroll)

    def show_search(self, *_,reset=True):
        self._navigate("search")
        self._builder_stage(False)
        if reset:
            self.security_search.text=""
        self._reset_scroll(self.search_scroll)

    def _builder_stage(self,selected,animate=False):
        self.builder_selected=selected
        self.page_titles["search"].text="Set your preference" if selected else "Choose a security"
        if selected and self.controls.parent is None:
            self.search_content.add_widget(self.controls)
        elif not selected and self.controls.parent is not None:
            self.search_content.remove_widget(self.controls)
        self.preference_reveal.show(selected,animate=animate)

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
        self.guide_content.add_widget(WrappedLabel(text=("Turquoise adjusted close (dividends included)" if self.yahoo_enabled
            else "Turquoise example close") + " · amber SMA/plus crossings. Drag to inspect; pinch to zoom.",color=MUTED,font_size=sp(11)))
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
        self.guide_status.text = "Loading the historical example…" if self.yahoo_enabled else "Calculating the educational example…"
        target = int(self.guide_target.text.split()[0])
        data = self.model.dataset
        def work():
            lesson_data = data
            if self.yahoo_enabled and not data.prices:
                provider = self.model.data_provider
                matches = provider.search("SPY")
                security = next((match for match in matches if match.ticker == "SPY"), None)
                if security is None:
                    raise ValueError("Example security unavailable. Select a company and try again.")
                lesson_data = provider.historical_data(security)
            return calculate_lesson(target,lesson_data if self.yahoo_enabled else None)
        future = self.market_executor.submit(work)
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
                lesson.dataset.dates,(result.period,result.sma),calendar_dates=self.yahoo_enabled,
                price_label="Adj. close" if self.yahoo_enabled else "EOD")
            self.guide_chart.set_timeline("3Y" if "3Y" in available_timelines(
                len(lesson.dataset.prices),lesson.dataset.dates if self.yahoo_enabled else ()) else "Max")
            name = self.model.security(lesson.dataset.counter).name if self.yahoo_enabled else "Educational example"
            self.guide_status.text = (f"{name} · {lesson.dataset.dates[report.start]} – {lesson.dataset.dates[report.end]}\n"
                f"SMA {result.period} · "
                f"target {result.target_frequency}/yr · observed {result.actual_annual_frequency:.2f}/yr · "
                f"{len(report.crossings.indices)} buys per comparison")
            prefix = "USD " if self.yahoo_enabled else "$"
            values = [f"a. Upward crossings: {prefix}{report.crossings.ending_value:,.2f}"]
            for key,title in (("dca","b. Equal periods"),("random","c. Most common random")):
                scenario = getattr(report,key)
                delta = scenario.difference_percent(report.crossings)
                difference = "N/A" if delta is None else f"{delta:+.2f}%"
                values.append(f"{title}: {prefix}{scenario.ending_value:,.2f} ({difference} vs a)")
            self.guide_values.text = "\n".join(values)
            if self.yahoo_enabled:
                self._update_api_status()
        except Exception as error:
            logging.exception("Guided example failed")
            self.guide_status.text = display_text(f"Could not load the example: {error}. Open it again to retry.")

    def show_parameters(self, *_):
        if self.yahoo_enabled and not self.model.dataset.prices:
            self.show_search()
            return
        self._navigate("search")
        self._show_selected_security(self.model.security(self.model.dataset.counter))
        self._builder_stage(True)
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
        self.sync_notification_schedule()

    def _navigate(self, name):
        self._before_navigation(name)
        self.finish_editing()
        self.saved_sheet.dismiss(animate=False)
        if name == "results":
            self._page_stack = (["library","results"] if self._result_origin == "library"
                                else ["library","search","results"])
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
        if current == "search" and destination != "search" and self.busy:
            self._job += 1
            self._cancel_optimization.set()
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
            if self.manager.current in ("search","library"):
                self._refresh_saved()

    @property
    def editors(self):
        return (self.security_search, self.custom_target, self.alert_session) + ((self.backtest_years,) if hasattr(self, "backtest_years") else ()) + ((self.rename_editor,) if hasattr(self,"rename_editor") else ())

    def finish_editing(self):
        for editor in self.editors:
            editor.focus = False

    def handle_back(self):
        """Consume overlays/editing first, then pages; only Library may exit."""
        for name in ("rename_popup","history_popup", "validation_popup", "backtest_help_popup", "api_log_popup", "clear_data_popup"):
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
                if editor is getattr(self,"rename_editor",None):
                    self._position_rename_popup()
                    return
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
        self.control_grid.cols = 1
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
        text = display_text(text)
        self.status.text = text
        self.status.color = ERROR if error else MUTED
        self.results_feedback.text = text
        self.results_feedback.color = ERROR if error else MUTED
        if quiet and self.results_feedback.parent is not None:
            self.results_footer.remove_widget(self.results_feedback)
        elif not quiet and self.manager.current == "results" and self.results_feedback.parent is None:
            self.results_footer.add_widget(self.results_feedback, index=0)
        if quiet and self.status.parent is not None:
            self.controls.remove_widget(self.status)
        elif not quiet and self.status.parent is None:
            self.controls.add_widget(self.status)

    def focus_security_search(self):
        self.show_search(reset=False)
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
        self._builder_stage(False)
        self.search_status.text = ("Press Enter or Submit to search." if self.yahoo_enabled else
                                   "Press Enter or Submit to search the examples.")
        self._set_busy(self.busy)

    def submit_security_search(self, *_, force=False):
        if self.manager.current != "search":
            self.show_search(reset=False)
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
        self.search_status.text = "Searching securities…" if self.yahoo_enabled else "Searching preview securities…"
        self.search_status.color = MUTED
        future = (self.market_executor.submit(self.model.data_provider.search, query, force=force)
                  if self.yahoo_enabled else self.market_executor.submit(self.model.data_provider.search, query))
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
            self.search_status.text = ((f"{len(matches)} matches. Select one to load daily price history."
                                       if matches else "No US/SG stock or ETF matches. Try the ticker (e.g. AAPL or D05.SI), or refresh results.")
                                      if self.yahoo_enabled else
                                      (f"{len(matches)} preview matches. Select one to load example history."
                                       if matches else "No preview matches. Try a partial ticker or company name, such as Apple or DBS."))
        except Exception as error:
            self._clear_security_matches()
            self.search_status.text = (display_text(error) if self.yahoo_enabled and isinstance(error, RuntimeError)
                                       else "Search could not be completed. Press Submit to try again.")
            self.search_status.color = ERROR
        self._update_api_status()

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
        scenario = self.model.data_provider.scenario if self.yahoo_enabled else self.scenario.text
        self._set_busy(False)
        self.search_status.text = (f"Loading all available daily history for {security.ticker}…"
                                   if self.yahoo_enabled else f"Loading example history for {security.ticker}…")
        self.search_status.color = MUTED
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
                self.scenario.values = (dataset.scenario,) if self.yahoo_enabled else SCENARIOS
                self.scenario.text = dataset.scenario
            finally:
                self._syncing_controls = False
            self._show_selected_security(security)
            self.refresh()
            self._builder_stage(True,animate=True)
            warning = getattr(self.model.data_provider, "last_warning", "")
            self.message(warning or ("History ready. Press Optimize SMA; MAX includes all downloaded history."
                                    if self.yahoo_enabled else "Example history loaded. Press Optimize SMA to calculate a result."),
                         error=bool(warning), quiet=not warning)
        except Exception as error:
            self.search_status.text = (display_text(error) if self.yahoo_enabled and isinstance(error, RuntimeError) else
                                      "Could not load history. Your previous security is unchanged; select a match to retry.")
            self.search_status.color = ERROR
        self._update_api_status()

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
        self.search_status.text = (f"Selected {security.ticker} · {security.name}. Daily history ready."
                                   if security.provider == "yahoo" else
                                   f"Selected {security.ticker} · {security.name}. Example history ready.")

    def on_dataset_change(self, *_):
        if self._syncing_controls:
            return
        self._job += 1
        self._history_token += 1
        self.history_loading = False
        try:
            self.model.select_dataset(self.counter.text, self.scenario.text)
            self._show_selected_security(security_by_key(self.counter.text))
            self.message("Example changed. Press Optimize SMA to calculate a new result.")
            self.refresh()
        except (ValueError, sqlite3.Error, OSError) as error:
            self.message(f"Could not load example: {error}", True)

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
        if self.yahoo_enabled and not self.model.dataset.prices:
            self.optimize_button.disabled = True
        for button in self.security_match_buttons:
            button.disabled = busy
        self.save_button.disabled = busy or self.model.result is None
        self.hide_button.disabled = busy or self.model.result is None

    def on_optimize(self, *_):
        if self.busy or self.history_loading:
            return
        if self.yahoo_enabled and not self.model.dataset.prices:
            self.show_search()
            self.search_status.text = "Choose a real company and load its daily history before optimizing."
            return
        self.show_parameters()
        self._result_origin = "parameters"
        try:
            self._read_target()
        except ValueError as error:
            self.message(str(error), True)
            return
        if self.model.reuse_result():
            self._job += 1
            self.refresh()
            self.show_results()
            self.scroll.scroll_y = 1
            self.message("Saved or cached SMA loaded.",quiet=True)
            return
        self._job += 1
        token = self._job
        self._calculation_job = token
        self._set_busy(True)
        self.message("Calculating all candidate periods across the full history…")
        self._cancel_optimization.set()
        self._cancel_optimization = Event()
        future = self.executor.submit(optimize_sma, self.model.dataset.prices, self.model.target_frequency,
                                      cancel=self._cancel_optimization)
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
            result = future.result()
            self.model.remember_result(result)
            self.model.apply_result(result)
            self.refresh()
            self.show_results()
            self.scroll.scroll_y = 1
            self.message("Optimization complete. Upward crossings are marked with outlined plus signs.", quiet=True)
        except (ValueError, sqlite3.Error, OSError) as error:
            self.message(f"Unable to optimize: {error}", True)
        except Exception:
            logging.exception("Unexpected optimization failure")
            self.message("Calculation failed unexpectedly. Try another security; details are in the log.", True)

    def on_save(self, *_):
        try:
            saved = self.model.toggle_current_saved()
            self.refresh()
            self.message("SMA line saved on this device." if saved else "SMA line unsaved. Restore it from the last-10 history.")
            if saved:
                self.expanded_saved_securities.add(self.model.dataset.counter)
                self._refresh_saved()
                self.saved_sheet.open()
            self.sync_notification_schedule()
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
            self.sync_notification_schedule()
        except (sqlite3.Error, OSError) as error:
            self.message(f"Could not remove saved line: {error}", True)

    def on_view_saved(self, line, *_):
        if self.manager.current != "results":
            self._result_origin = "library" if self.manager.current == "library" else "parameters"
        if self.busy:
            return
        if line.counter.startswith("YAHOO:") and self.yahoo_enabled:
            self._job += 1
            self._history_token += 1
            token = self._history_token
            # Cached View should open even while the startup network probe is pending.
            if self.model.data_provider.cache.history(line.counter)[0]:
                try:
                    cached = self.model.data_provider.cached_data(self.model.security(line.counter))
                    completed = Future()
                    completed.set_result((line, cached, self.model.result_for_dataset(
                        cached, line.period, line.target_frequency)))
                    self._saved_history_complete(completed, token)
                    if not cached.stale:
                        return
                except (ValueError, RuntimeError):
                    pass
            self.history_loading = True
            self._set_busy(False)
            future = self.market_executor.submit(self.model.prepare_saved_line, line.id)
            future.add_done_callback(lambda done: self._on_ui(lambda: self._saved_history_complete(done, token)))
            return
        try:
            self._job += 1
            selected = self.model.view_saved_line(line.id)
            self._syncing_controls = True
            try:
                self.scenario.values = SCENARIOS
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
            self.message(f"Viewing {selected.display_name} for {selected.counter} · {selected.scenario}.", quiet=True)
        except (ValueError, sqlite3.Error, OSError) as error:
            self.message(f"Could not open saved SMA: {error}", True)

    def _saved_history_complete(self, future, token):
        if token != self._history_token:
            return
        self.history_loading = False
        self._set_busy(False)
        try:
            prepared = future.result()
            # Revalidate: the user may have unsaved the line during its fetch.
            self.model.store.get_line(prepared[0].id)
            self.model.apply_saved_line(prepared)
            selected = prepared[0]
            self._syncing_controls = True
            try:
                self.counter.text = selected.counter
                self.scenario.values = (selected.scenario,)
                self.scenario.text = selected.scenario
                self.custom_target.text = str(selected.target_frequency)
                self.target.text = (f"{selected.target_frequency} / year"
                                    if selected.target_frequency in TARGET_FREQUENCIES else "Custom")
            finally:
                self._syncing_controls = False
            self._show_selected_security(self.model.security(selected.counter))
            self.refresh()
            self.chart.set_timeline("1Y")
            self.show_results()
            warning = getattr(self.model.data_provider, "last_warning", "")
            self.message(warning or f"Viewing {selected.display_name} ({selected.period} sessions).", bool(warning), quiet=not warning)
        except (ValueError, RuntimeError, sqlite3.Error, OSError) as error:
            self.message(f"Could not open saved SMA: {error}", True)
            self.source_warning.text = display_text(error)
            self._refresh_saved()
        self._update_api_status()

    def refresh(self):
        self.last_alerts = ()
        self.alert_preview.text = "No current preview. Choose a session and press Preview EOD alerts."
        data = self.model.dataset
        live = not getattr(data, "is_simulated", True)
        self.alert_session_label.text = f"Test an end-of-day session (1–{len(data.prices)})"
        if live:
            self.alert_session.text = str(len(data.prices))
        if live and self.scenario_cell.parent is not None:
            self.scenario_cell.parent.remove_widget(self.scenario_cell)
        elif not live and self.scenario_cell.parent is None:
            self.custom_panel.add_widget(self.scenario_cell)
        self.plot_title.set_security(self.model.security(data.counter))
        lines = self.model.plot_lines()
        self.chart.update(data.prices, lines, data.dates,
                          (self.model.result.period, self.model.result.sma) if self.model.result else None,
                          calendar_dates=live,price_label="Adj. close" if live else "EOD",
                          inspection_name=self.model.current_line_name())
        self._refresh_chart_header()
        self.legend.clear_widgets()
        close_label = f"adj. close ({data.currency})" if live and data.prices else "adj. close" if live else "example close"
        self.legend_labels = [close_label, "upward crossings"]
        def add_legend(text, color, plus=False):
            item = LegendItem(text, color, plus=plus)
            item.bind(width=self._center_legend)
            self.legend.add_widget(item)

        add_legend(close_label, PRICE_COLOR)
        add_legend("upward crossings", MUTED, plus=True)
        for index, line in enumerate(lines):
            label = line.name or f"SMA {line.period}"
            self.legend_labels.append(label)
            add_legend(label, self.chart.line_color(line, index))
        for key, value in self.model.summary().items():
            if key in self.card_values:
                self.card_values[key].text = value
        saved=self.model.current_saved_line()
        self.selected_target_badge.text=f"Target\n{self.model.result.target_frequency if self.model.result else self.model.target_frequency} / year"
        self.named_period_caption.text=f"{self.model.result.period} sessions" if saved and saved.custom_name else ""
        if saved and self.rename_button.parent is None:
            self.line_name_row.add_widget(self.rename_button,index=1)
        elif not saved and self.rename_button.parent is not None:
            self.line_name_row.remove_widget(self.rename_button)
        self.card_values["period"].color = (saved_color(self.model.store.color_index(
            data.counter,data.scenario,self.model.result.period)) if self.model.result else ACTIVE_COLOR)
        self._set_busy(self.busy)
        self.save_button.selected = self.model.current_saved_line() is not None
        self.optimal_caption.text = ("SAVED SMA" if self.model.viewing_saved else
                                     "SELECTED SMA" if self.model.period_preserved else "OPTIMAL SMA")
        self.hide_button.text = "Hide SMA" if self.model.active_visible else "Show SMA"
        result = self.model.result
        self.explanation.text = (
            f"Based on {result.comparisons} usable comparisons "
            f"({result.usable_years:.2f} trading years) from {result.history_sessions} sessions. "
            f"Target difference: {float(result.frequency_error):.2f}/yr. " +
            ("Viewing the exact selected period. " if self.model.viewing_saved or self.model.period_preserved else
             f"SMA search: 2–{maximum_sma_period(result.history_sessions)}. ") +
            "Warm-up and gaps are excluded. "
            + ("Parameters have not been re-optimized." if self.model.viewing_saved or self.model.period_preserved else
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
        self.timeline_selector.values = available_timelines(len(data.prices),
                                    data.dates if not getattr(data, "is_simulated", True) else ())
        self.timeline_selector.text = self.chart.timeline
        self.timeline_selector.disabled = not data.prices
        self.plot_subtitle.text = f"EDUCATIONAL EXAMPLE · {len(data.prices)} sessions · example price units\nCrossing markers estimate daily-line intersections."
        if not getattr(data, "is_simulated", True) and data.prices:
            from .schedule import SGT
            fetched = datetime.fromtimestamp(data.fetched_at, SGT).strftime("%Y-%m-%d %H:%M SGT")
            self.plot_subtitle.text = (f"{data.currency} adjusted daily close · {len(data.prices)} sessions\n"
                                      f"Last close {data.dates[-1]} · fetched {fetched}\n"
                                      "Dividends/splits included; crossing fills are daily-line estimates.")
            if data.stale:
                self.plot_subtitle.text += "\nSaved data · refresh pending or unavailable."
        elif not getattr(data, "is_simulated", True):
            self.plot_subtitle.text = "Choose a company to download daily price history."
        if data.prices:
            start, end = self.chart.view_range
            first,last = max(0,math.ceil(start)),min(len(data.prices)-1,math.floor(end))
            self.plot_subtitle.text += f"\n{self.chart.timeline} view · {data.dates[first]} – {data.dates[last]}"

    def _refresh_saved(self):
        self.saved_rows = self._populate_saved_panel(self.saved_panel, self.model.library_lines())
        self.landing_saved_rows = self._populate_saved_panel(
            self.landing_saved_panel, self.model.library_lines(), landing=True)
        self.library_content.clear_widgets()
        self.library_state = "populated" if self.model.library_lines() else "empty"
        widgets = ([self.new_analysis_button,self.landing_saved_panel,self.library_intro] if self.library_state == "populated"
                   else [self.library_intro,self.new_analysis_button,self.library_archive_button])
        if self.yahoo_enabled and self.library_state == "empty":
            widgets = [self.new_analysis_button, self.library_intro, self.library_archive_button]
        if self.source_warning.text:
            widgets.insert(0, self.source_warning)
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
        label = f"{line.display_name}" + (f" · SMA {line.period}" if line.custom_name else "") + f" · target {line.target_frequency}/yr"
        if len(self.model.dataset.prices) >= 4 and line.period > maximum_sma_period(len(self.model.dataset.prices)):
            label += " · saved previously; outside current search limit"
        title = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(5))
        active = (self.model.result is not None and self.model.result.period == line.period
                  and (line.counter, line.scenario) == (self.model.dataset.counter, self.model.dataset.scenario))
        swatch = LegendSymbol(saved_color(self.model.store.color_index(line.counter,line.scenario,line.period)))
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
        if self.yahoo_enabled and platform=="android" and not line.push_enabled:
            try:
                AndroidNotifier.request_permission(lambda allowed:self._on_ui(
                    lambda:self._apply_line_alert(line.id,True) if allowed else
                    self.message("Notification permission was not granted. Enable it in Android Settings to turn this SMA on.",True)))
            except RuntimeError as error:
                self.message(str(error),True)
            return
        self._apply_line_alert(line.id,not line.push_enabled)

    def _apply_line_alert(self,line_id,enabled):
        try:
            self.model.store.get_line(line_id)
            self.model.store.set_notifications(line_id,"phone",enabled)
            self.refresh()
            self.sync_notification_schedule()
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

    def sync_notification_schedule(self,*_):
        if self.closed or not self.yahoo_enabled:
            return
        try:
            from .native_schedule import sync_schedules
            self.notification_status.text=sync_schedules(self.model.store,self.model.data_provider,platform)
            if platform=="android" and not self.model.data_provider.cache.preference("android_notification_permission_asked_v1",False):
                from .daily_notifications import enabled_lines
                if enabled_lines(self.model.store,self.model.data_provider):
                    # Existing enabled preferences need the same OS consent as
                    # a newly enabled line. Ask once; explicit On/Test can retry.
                    self.model.data_provider.cache.set_preference("android_notification_permission_asked_v1",True)
                    AndroidNotifier.request_permission(lambda allowed:self._on_ui(self.sync_notification_schedule))
        except Exception:
            logging.exception("Native daily schedule could not be configured")
            self.notification_status.text="Daily scheduling could not be configured. Reopen Settings and share the request log."

    def resume_cached_prices(self):
        """Show a completed native refresh on return, with no extra API call."""
        if not self.yahoo_enabled or self.closed or self.busy or self.history_loading:
            return
        current=self.model.dataset
        if not current.prices:
            return
        try:
            _,_,revision=self.model.data_provider.cache.history(current.counter)
            if revision==current.revision:
                return
            data=self.model.data_provider.cached_data(self.model.security(current.counter))
            result=self.model.result
            was_saved=self.model.viewing_saved
            was_visible=self.model.active_visible
            prepared=self.model.result_for_dataset(data,result.period,result.target_frequency) if result else None
            self.model.apply_dataset(data)
            if prepared:
                self.model.apply_result(prepared)
                self.model.viewing_saved=was_saved
                self.model.period_preserved=True
            self.model.active_visible=was_visible
            self.refresh()
        except (RuntimeError,ValueError,sqlite3.Error,OSError) as error:
            self.message(f"Could not open the refreshed cache: {error}",True)

    def open_unsaved_history(self, *_):
        content = BoxLayout(orientation="vertical", spacing=dp(10),padding=dp(10))
        content.add_widget(WrappedLabel(text="Last 10 unsaved lines · all counters/scenarios. Older entries are discarded.",color=MUTED))
        scroll = ScrollView(do_scroll_x=False)
        entries = BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(10))
        entries.bind(minimum_height=entries.setter("height"))
        self.history_restore_buttons = {}
        self.history_identities = {}
        for line in self.model.archive_lines():
            entry = SavedSecurityGroup()
            identity = SecurityIdentity(security_by_key(line.counter), logo_size=dp(20),
                                         height=dp(32), font_size=sp(12))
            entry.add_widget(identity)
            entry.add_widget(WrappedLabel(text=f"{line.display_name}" + (f" · SMA {line.period}" if line.custom_name else "") + f" · target {line.target_frequency}/yr",
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
            self.sync_notification_schedule()
            self.message(f"Restored {line.display_name} for {line.counter} · {line.scenario}.")
        except (ValueError,sqlite3.Error) as error:
            self.history_status.text = str(error)

    def _build_notification_settings(self):
        self.settings_panel = Panel()
        self.settings_content.add_widget(self.settings_panel)
        self.settings_panel.add_widget(WrappedLabel(text="04  /  NOTIFICATION SETTINGS",bold=True,color=MUTED,font_size=sp(11)))
        self.settings_panel.add_widget(WrappedLabel(
            text=("Only saved SMAs with notifications switched on are checked. US: Tuesday–Saturday at 6:30am; "
                  "SGX: Monday–Friday at 6:30pm, Singapore time. Choose the signal types below. "
                  "Android may delay a background check while sleeping or offline."
                  if self.yahoo_enabled else
                  "SIMULATED DATA · Manual EOD tests. Preview sends nothing; Send enabled alerts posts phone notifications."),
            color=MUTED,font_size=sp(11)))
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
        if self.yahoo_enabled:
            self.preview_alert_button.disabled = True
            self.phone_test_button.disabled = platform!="android"
            self.eod_deliver_button.disabled = True
            self.notification_status.text = "Daily checks use the enabled saved SMAs and signal types."
            for widget in (self.alert_session_label,test_row,self.preview_alert_button,self.eod_deliver_button,self.alert_preview):
                if widget.parent is not None:
                    widget.parent.remove_widget(widget)

    def _build_api_settings(self):
        panel = Panel()
        self.settings_content.add_widget(panel)
        panel.add_widget(WrappedLabel(text=f"DATA CONNECTION · {APP_VERSION}", bold=True))
        panel.add_widget(WrappedLabel(
            text="Requests run on launch, your actions, or enabled daily notification checks. "
                 "Downloaded history survives closing the app.",
            color=MUTED, font_size=sp(12)))
        self.api_status = WrappedLabel(text="No data request completed yet.", color=MUTED, font_size=sp(12))
        panel.add_widget(self.api_status)
        for title, name, callback in (
            ("Check data connection", "api_check_button", lambda _: self.check_yahoo_source(force=True)),
            ("Refresh selected prices", "api_refresh_button", lambda _: self.refresh_current_prices()),
            ("Refresh all selected history", "api_full_button", lambda _: self.refresh_current_prices(full=True)),
            ("View data request log", "api_log_button", self.show_api_log),
            ("Clear downloaded prices and search results", "api_clear_button", self.confirm_clear_market_data),
        ):
            button = LabButton(text=title)
            setattr(self, name, button)
            button.bind(on_release=callback)
            panel.add_widget(button)

    def _update_api_status(self):
        if not hasattr(self, "api_status"):
            return
        from .schedule import SGT
        operations = self.model.data_provider.cache.operations(1)
        if operations:
            at, operation, symbol, status, detail = operations[0]
            self.api_status.text = display_text(f"Last event: {operation} · {symbol} · {status}\n"
                                    f"{datetime.fromtimestamp(at, SGT):%Y-%m-%d %H:%M:%S} SGT"
                                    + (f"\n{detail}" if detail else ""))
            self.api_status.color = ERROR if status in ("failed","stale","deferred") else MUTED
        blocked = self._source_check_busy or self.history_loading or self.search_busy or self.busy
        for name in ("api_check_button", "api_refresh_button", "api_full_button", "api_clear_button"):
            getattr(self, name).disabled = blocked

    def check_yahoo_source(self, *_, force=False):
        if self.closed or not self.yahoo_enabled or self._source_check_busy:
            return
        self._source_check_busy = True
        self._update_api_status()
        future = self.market_executor.submit(self.model.data_provider.health_check, force=force)
        future.add_done_callback(lambda done: self._on_ui(lambda: self._source_check_complete(done, force)))

    def _source_check_complete(self, future, explicit):
        self._source_check_busy = False
        try:
            success, warning = future.result()
        except Exception:
            success, warning = False, "Unable to check the data connection from this device. Saved data remains available."
        self.source_warning.text = "" if success else display_text(warning)
        self._refresh_saved()
        # Startup success stays quiet. Explicit tests have a result in Settings.
        if explicit and success:
            self.api_status.text = "Data connection check succeeded."
        self._update_api_status()

    def refresh_current_prices(self, *_, full=False):
        if self.closed or self.history_loading or self.busy:
            return
        data, result = self.model.dataset, self.model.result
        if getattr(data, "is_simulated", True) or not data.prices:
            self.api_status.text = "Select a company first to load its daily price history."
            return
        self._history_token += 1
        token = self._history_token
        self.history_loading = True
        self._set_busy(False)
        was_saved = self.model.viewing_saved
        security = self.model.security(data.counter)
        def work():
            updated = self.model.data_provider.historical_data(security, force=True, full=full)
            updated_result = (self.model.result_for_dataset(updated, result.period, result.target_frequency)
                              if result else None)
            return updated, updated_result
        future = self.market_executor.submit(work)
        future.add_done_callback(lambda done: self._on_ui(
            lambda: self._refresh_history_complete(done, token, was_saved)))
        self._update_api_status()

    def _refresh_history_complete(self, future, token, was_saved):
        if token != self._history_token:
            return
        self.history_loading = False
        self._set_busy(False)
        try:
            data, result = future.result()
            self.model.apply_dataset(data)
            if result:
                self.model.apply_result(result)
                self.model.viewing_saved = was_saved
                self.model.period_preserved = True
            self.refresh()
            warning = getattr(self.model.data_provider, "last_warning", "")
            if not data.stale:
                self.source_warning.text = ""
            self.api_status.text = display_text(warning) if warning else f"History refreshed through {data.dates[-1]}. Selected SMA period is unchanged."
            self.message(self.api_status.text, bool(warning), quiet=not warning)
        except (ValueError, RuntimeError, OSError, sqlite3.Error) as error:
            self.api_status.text = display_text(error)
        self._update_api_status()

    def show_api_log(self, *_):
        from .diagnostics import diagnostic_report
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        self.api_log_status = WrappedLabel(text="Copy this report to share an error. HTTP rows show network requests; CACHE rows send none.",
                                           color=MUTED,font_size=sp(11))
        content.add_widget(self.api_log_status)
        self.api_log_limit = 100
        self.api_log_scroll = ScrollView(do_scroll_x=False,bar_width=dp(4),scroll_type=["content","bars"])
        self.api_log_entries = BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(8))
        self.api_log_entries.bind(minimum_height=self.api_log_entries.setter("height"))
        self.api_log_scroll.add_widget(self.api_log_entries)
        content.add_widget(self.api_log_scroll)
        def refresh(*_):
            self._reset_scroll(self.api_log_scroll)
            self.api_log_report = diagnostic_report(
                self.model.data_provider.cache,platform,
                getattr(self.model.data_provider,"transport_name","Test transport"),
                self.model.dataset,limit=self.api_log_limit,public_view=True)
            self.api_log_entries.clear_widgets()
            # Separate small textures avoid the GPU size limit of one giant label.
            for block in self.api_log_report.split("\n\n"):
                card = Panel()
                card.add_widget(WrappedLabel(text=block,font_size=sp(11)))
                self.api_log_entries.add_widget(card)
            self.api_log_scroll.scroll_y = 1
        def older(*_):
            previous_limit = self.api_log_limit
            self.api_log_limit += 100
            refresh()
            cards = list(reversed(self.api_log_entries.children))
            if len(cards)>previous_limit+1:
                first_older = cards[previous_limit+1]
                def reveal(*_):
                    if first_older.parent is self.api_log_entries:
                        self.api_log_scroll.scroll_to(first_older,padding=dp(4),animate=False)
                Clock.schedule_once(reveal,.1)
        def copy(*_):
            try:
                from kivy.core.clipboard import Clipboard
                Clipboard.copy(self.api_log_report)
                self.api_log_status.text = "Report copied. Paste it into this chat with the action that failed."
            except Exception:
                self.api_log_status.text = "Clipboard unavailable. Share a screenshot of the relevant calls."
        for title, callback in (("Copy diagnostic report",copy),("Refresh log (no API call)",refresh),
                                ("Load older calls",older)):
            button = LabButton(text=title)
            button.bind(on_release=callback)
            content.add_widget(button)
        close = LabButton(text="Close")
        content.add_widget(close)
        popup = Popup(title="Request log · newest first", content=content, size_hint=(.94,.88))
        self.api_log_popup = popup
        close.bind(on_release=popup.dismiss)
        refresh()
        popup.open()

    def confirm_clear_market_data(self, *_):
        if self.history_loading or self.search_busy or self._source_check_busy:
            return
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        content.add_widget(WrappedLabel(
            text="Clear downloaded prices and cached search results? Saved SMA parameters, company identities "
                 "and preferences will remain. Opening a saved line afterwards needs a download."))
        cancel, clear = LabButton(text="Cancel"), LabButton(text="Clear downloaded data")
        content.add_widget(cancel)
        content.add_widget(clear)
        popup = Popup(title="Clear downloaded data?", content=content, size_hint=(.94,None), height=dp(300))
        self.clear_data_popup = popup
        cancel.bind(on_release=popup.dismiss)
        def confirmed(*_):
            self.model.data_provider.cache.clear_downloads()
            self.model.apply_dataset(self.model.data_provider.initial_dataset())
            self._syncing_controls = True
            try:
                self.counter.text = self.model.dataset.counter
                self.scenario.values = (self.model.dataset.scenario,)
                self.scenario.text = self.model.dataset.scenario
            finally:
                self._syncing_controls = False
            popup.dismiss()
            self.refresh()
            self.show_library()
            self.api_status.text = "Downloaded data cleared; saved SMA parameters are retained."
        clear.bind(on_release=confirmed)
        popup.open()

    def on_notification_rule(self, key, active):
        if getattr(self,"_reverting_rule",False):
            return
        try:
            settings = replace(self.model.store.notification_settings(), **{key:active})
            self.model.store.save_notification_settings(settings)
            self.sync_notification_schedule()
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
                                    for alert in evaluate_dataset_eod(self.model.dataset,line,settings,session)
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
                          "SMA Stock Analyzer · Test", "Notification test · Phone notifications are working."
                          if self.yahoo_enabled else "SIMULATED TEST · Phone notifications are working.")
            AndroidNotifier().send(alert)
            self.notification_status.text = "Android test notification posted. Check the notification shade."
            self.sync_notification_schedule()
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
        for title in (("Date" if self.yahoo_enabled else "Session"),"Crossing price","SMA at cross"):
            table.add_widget(Label(text=title,color=MUTED,font_size=sp(12)))
        for row in rows:
            for value in row:
                table.add_widget(Label(text=value,color=TEXT,font_size=sp(12)))
        return table

    def _refresh_table(self):
        # Keep the controls alive: refreshing after a save/hide must retain the period.
        if not hasattr(self, "backtest_period"):
            self.backtest_section_title=WrappedLabel(text="",font_size=sp(11),color=MUTED)
            self.table_panel.add_widget(self.backtest_section_title)
            self.backtest_header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
            self.backtest_heading = WrappedLabel(text="If you invested $100 per buy for the past:", bold=True, font_size=sp(14))
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
            self.backtest_contribution = WrappedLabel(font_size=sp(13))
            self.table_panel.add_widget(self.backtest_contribution)
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
                else:
                    self.backtest_gain_icon = IconSymbol(kind="gain",size_hint=(None,None),
                                                        size=(dp(18),dp(24)),pos_hint={"center_y":.5})
                    value_row.add_widget(self.backtest_gain_icon)
                    self.backtest_gain = Label(text="",size_hint_x=None,font_size=sp(12),color=PRICE_COLOR)
                    self.backtest_gain.bind(texture_size=lambda widget,size:setattr(widget,"width",size[0]+dp(2)))
                    value_row.add_widget(self.backtest_gain)
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
        self.backtest_section_title.text=f"03  /  BACKTESTING · {self.model.current_line_name()}"
        self._refresh_backtest()

    def show_rename_line(self,*_):
        saved=self.model.current_saved_line()
        if saved is None:
            return
        self.finish_editing()
        content=BoxLayout(orientation="vertical",spacing=dp(10),padding=dp(12))
        scroll=ScrollView(do_scroll_x=False)
        fields=BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(8))
        fields.bind(minimum_height=fields.setter("height"))
        fields.add_widget(WrappedLabel(text=f"SMA {saved.period} · target {saved.target_frequency}/year. Leave blank to use the default name.",color=MUTED))
        self.rename_editor=EditingField(text=saved.custom_name,hint_text="Name your saved SMA",multiline=False,
            size_hint_y=None,height=dp(48),font_size=sp(16),padding=dp(10),foreground_color=TEXT,
            background_normal="",background_active="",background_color=(.10,.15,.23,1))
        fields.add_widget(self.rename_editor)
        self.rename_status=WrappedLabel(text="",color=ERROR,font_size=sp(12))
        fields.add_widget(self.rename_status)
        scroll.add_widget(fields)
        content.add_widget(scroll)
        buttons=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(8))
        cancel=LabButton(text="Cancel")
        self.rename_save_button=LabButton(text="Save name",primary=True)
        buttons.add_widget(cancel)
        buttons.add_widget(self.rename_save_button)
        content.add_widget(buttons)
        self.rename_popup=ScreenPopup(self,title="Name saved SMA",content=content,size_hint=(None,None))
        self.bind(size=self._position_rename_popup,pos=self._position_rename_popup)
        def dismiss(*_):
            self.rename_editor.focus=False
            self.unbind(size=self._position_rename_popup,pos=self._position_rename_popup)
        self.rename_popup.bind(on_dismiss=dismiss)
        cancel.bind(on_release=self.rename_popup.dismiss)
        def save_name(*_):
            try:
                self.model.store.rename(saved.id,self.rename_editor.text)
                self.rename_popup.dismiss()
                self.refresh()
            except (ValueError,sqlite3.Error) as error:
                self.rename_status.text=str(error)
        self.rename_save_button.bind(on_release=save_name)
        self.rename_editor.bind(on_text_validate=save_name,focus=self._editor_focus)
        self._position_rename_popup()
        self.rename_popup.open()
        Clock.schedule_once(lambda _:setattr(self.rename_editor,"focus",True) if self.rename_popup._is_open else None,.1)

    def _position_rename_popup(self,*_):
        popup=getattr(self,"rename_popup",None)
        if popup is not None:
            popup.size=(min(dp(500),self.width*.94),min(dp(290),max(dp(180),self.height-dp(24))))
            popup.pos=(self.center_x-popup.width/2,self.center_y-popup.height/2)

    def _refresh_backtest(self, *_):
        custom = self.backtest_period.text == "Custom"
        if custom and self.backtest_custom_row.parent is None:
            self.backtest_custom_holder.add_widget(self.backtest_custom_row)
        elif not custom and self.backtest_custom_row.parent is not None:
            self.backtest_custom_holder.remove_widget(self.backtest_custom_row)
            self.backtest_years.focus = False
        self.backtest_custom_holder.height = dp(44) if custom else 0
        self.backtest_report = None
        self.backtest_contribution.text = ""
        self.backtest_gain.text = ""
        self.backtest_gain_icon.opacity = 0
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
            dates = data.dates if not getattr(data, "is_simulated", True) else None
            self.backtest_heading.text = ("If you invested USD 100 per buy for the past:"
                                          if dates else "If you invested $100 per buy for the past:")
            sessions = period_sessions(self.backtest_period.text, self.backtest_years.text, len(data.prices), dates)
            report = compare_investments(data.prices, result.sma, result.events, sessions, dates)
            self.backtest_report = report
            count = len(report.crossings.indices)
            self._set_backtest_captions(count)
            from datetime import date
            years = ((date.fromisoformat(data.dates[report.end])-date.fromisoformat(data.dates[report.start])).days/365.2425
                     if dates else (report.end-report.start+1)/252)
            prefix = "USD " if dates else "$"
            self.backtest_contribution.text = (f"Over {years:.2f} years, following {count} upward crossings, "
                f"you would have invested {prefix}{report.crossings.invested:,.0f} in total ({count} × {prefix}100).")
            self.backtest_details.text = ""
            gain = report.crossings.return_percent
            if gain is not None:
                self.backtest_gain_icon.kind = "gain" if gain>=0 else "loss"
                self.backtest_gain_icon.opacity = 1
                self.backtest_gain.text = f"{gain:+.2f}%"
                self.backtest_gain.color = (.22,.94,.43,1) if gain>=0 else ERROR
            else:
                self.backtest_gain.text = "N/A"
            self.backtest_note.text = (
                f"Scenario a's moving average strategy outperforms {report.outperformance_percent:.1f}% of all 500 random buy scenarios."
                if report.outperformance_percent is not None else
                "Scenario a's moving average strategy outperformance is N/A: no upward crossings in this period.")
            for key, value in self.backtest_values.items():
                scenario = getattr(report, key)
                value.text = f"{prefix}{scenario.ending_value:,.2f}"
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
            text = ("This scenario follows the popular dollar cost averaging strategy. "
                    + ("It invests USD 100 at the dividend/split-adjusted daily close " if self.yahoo_enabled
                       else "It invests $100 at the EOD price ") + "at the start of each of N equal periods, "
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
            text=f"{self.model.security(data.counter).name} · {self.model.current_line_name()} · {result.period} sessions · target {result.target_frequency}/yr · {result.crossing_count} upward crossings", bold=True))
        self.full_crossover_table = self._crossing_table(self.model.event_rows())
        self.full_table_panel.add_widget(self.full_crossover_table)
        self._navigate("crossovers")
        self.full_crossovers_scroll.scroll_y = 1

    def close(self):
        self.closed = True
        self._cancel_optimization.set()
        self._editor_scroll_trigger.cancel()
        self.finish_editing()
        self._search_token += 1
        self._history_token += 1
        self._guide_job += 1
        self.preference_reveal.show(False)
        self.chart._cancel_selection()
        self.guide_chart._cancel_selection()
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
            if configured:
                directory = Path(configured)
            elif platform not in ("android", "ios"):
                from .paths import data_directory
                directory = data_directory()
            else:
                directory = Path(self.user_data_dir)
            from .providers import create_provider
            source = os.environ.get("SMA_DATA_SOURCE","yahoo")
            provider = create_provider(directory,platform,source)
            self.screen = AnalyzerScreen(AnalyzerModel(LineStore(directory / "saved_lines.sqlite3"), provider))
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

    def on_resume(self):
        if hasattr(self,"screen"):
            self.screen.resume_cached_prices()
            self.screen.sync_notification_schedule()

    def on_stop(self):
        Window.unbind(on_keyboard=self._on_keyboard)
        if hasattr(self, "android_window"):
            self.android_window.stop()
        if hasattr(self, "screen"):
            self.screen.close()
