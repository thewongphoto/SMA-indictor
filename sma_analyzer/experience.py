"""Four-tab presentation layered over the existing calculation and data flows."""
import sqlite3
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from .theme import ACCENT, ACCENT_TINT, ON_ACCENT, BG, SURFACE, CONTROL, MUTED, TEXT, NEGATIVE
from .widgets import (SecurityIdentityButton, RuleSwitch, PreferenceReveal, IconButton, SavedSecurityGroup, Pill,
                      LinesToggle, SavedLineRow, ChangeValue)
from kivy.uix.anchorlayout import AnchorLayout
from .watchlist import watchlist, line_state
from kivy.clock import Clock
from kivy.graphics import Line, Rectangle
from .appearance import Color


class Experience:
    def build_experience(self):
        from .app import Panel, LabButton, WrappedLabel
        page = Screen(name='alerts')
        self.pages['alerts'] = page
        self.manager.add_widget(page)
        self.alerts_scroll, self.alerts_content = self._scrolling_page('alerts')
        self._page_heading('alerts', 'Alerts')
        self.tab_bar = BoxLayout(size_hint=(1, None), height=dp(58), pos_hint={'x': 0, 'y': 0},
                                 padding=(dp(8), dp(5)), spacing=dp(4))
        self.tab_buttons = {}
        for key, title in [('library','Home'),('results','Charts'),('alerts','Alerts'),('settings','Settings')]:
            button = LabButton(text=title)
            button.bind(on_release=lambda _, destination=key: self.select_tab(destination))
            self.tab_buttons[key] = button
            self.tab_bar.add_widget(button)
        self.add_widget(self.tab_bar)
        from .theme import DIVIDER
        with self.tab_bar.canvas.before:
            Color(*BG)
            tab_fill = Rectangle()
            Color(*DIVIDER)
            tab_line = Rectangle()
        def paint_tab_bar(bar, *_):
            tab_fill.pos, tab_fill.size = bar.pos, bar.size
            tab_line.pos, tab_line.size = (bar.x, bar.top - dp(1)), (bar.width, dp(1) if bar.height else 0)
        self.tab_bar.bind(pos=paint_tab_bar, size=paint_tab_bar)
        self.bind(size=self.layout_tabs, pos=self.layout_tabs)
        self.manager.bind(current=self.update_tabs)
        self.page_titles['library'].text = 'Home'
        self.page_titles['library'].font_size = sp(28)
        self.page_titles['search'].text = 'Find a security'
        self.new_analysis_button.text = '+ Find SMA'
        self.new_analysis_button.size_hint_x=None
        self.new_analysis_button.width=dp(112)
        self.style_outline_pill(self.new_analysis_button)
        self.page_titles['library'].parent.add_widget(self.new_analysis_button)
        self.search_submit.text = 'Search'
        self.security_search.hint_text = 'Company name or ticker'
        self.security_search.font_size = sp(16)
        self.restructure_search()
        # Presets drive the existing validated target selector and custom input.
        self.target_row.remove_widget(self.target)
        self.frequency_chips = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        self.frequency_buttons = {}
        for value in (4, 6, 12, 'Custom'):
            button = LabButton(text=str(value))
            button.bind(on_release=lambda _, value=value: setattr(self.target, 'text',
                'Custom' if value == 'Custom' else f'{value} / year'))
            self.frequency_buttons[value] = button
            self.frequency_chips.add_widget(button)
        self.target_row.add_widget(self.frequency_chips, index=len(self.target_row.children))
        self.target.bind(text=self.refresh_frequency_chips)
        self.target.bind(text=lambda *_: self.refresh_detail_frequency())
        self.refresh_frequency_chips()
        self.optimize_button.bind(size=lambda button, _: setattr(button, 'text_size', (button.width-dp(16), None)))
        self.home_summary = Panel()
        self.home_summary_caption = WrappedLabel(text='', color=MUTED, font_size=sp(13))
        self.home_summary_title = WrappedLabel(text='Your saved lines', bold=True, font_size=sp(26))
        self.home_summary_note = WrappedLabel(text='', color=MUTED, font_size=sp(15))
        self.home_summary.add_widget(self.home_summary_caption)
        self.home_summary.add_widget(self.home_summary_title)
        self.home_summary.add_widget(self.home_summary_note)
        self.inline_lines = Panel()
        self.build_detail_layout()
        # Design 13: data-connection problems are a calm warning card, not red text.
        from .theme import WARNING_BG, WARNING_TITLE, WARNING_TEXT
        self.source_warning_card = Panel()
        self.source_warning_card._panel_color.rgba = WARNING_BG
        self.source_warning_card.add_widget(WrappedLabel(text="Can't reach market data", bold=True,
                                                         color=WARNING_TITLE, font_size=sp(16)))
        self.source_warning.color = WARNING_TEXT
        self.source_warning.font_size = sp(14)
        self.source_warning_card.add_widget(self.source_warning)
        self.source_warning_card.add_widget(WrappedLabel(text='Showing prices saved on this phone. Search and new '
                                                              'calculations need a connection.',
                                                         color=WARNING_TEXT, font_size=sp(13)))
        self.library_intro.children[-1].text = 'No saved SMA lines yet'
        self.library_intro.children[-1].font_size = sp(24)
        self.library_intro.children[-2].text = ('Find a stock or ETF, pick how often you want buy signals, and save '
                                                'the line. Saved lines appear here.')
        self.library_intro.children[-2].font_size = sp(15)
        self.library_intro._panel_color.rgba = BG
        self.library_intro.padding = (0, dp(48), 0, dp(8))
        self.library_intro.spacing = dp(14)
        find=LabButton(text='Find a security',primary=True)
        find.height = dp(52)
        find.font_size = sp(16)
        find.bind(on_release=self.show_search)
        self.library_intro.add_widget(find,index=1)
        self.guide_button.text = 'Try the guided example'
        self.guide_button.fill = BG
        self.guide_button.font_size = sp(15)
        self.guide_button._draw()
        self.library_archive_button.fill = BG
        self.library_archive_button.color = MUTED
        self.library_archive_button._draw()
        self.build_appearance()
        self.restructure_settings()
        self.build_signup()
        self.layout_tabs()
        self.update_tabs()

    def style_outline_pill(self, button):
        """Design '+ Find SMA': teal text, 1 dp teal-tinted outline, fully rounded, no fill."""
        from .theme import ACCENT_BORDER
        button.fill = BG
        button.color = ACCENT
        button.font_size = sp(14)
        button.width = dp(116)
        button.height = dp(40)
        button.pos_hint = {'center_y': .5}
        button._draw()
        with button.canvas.after:
            Color(*ACCENT_BORDER)
            outline = Line(width=dp(1))
        def paint(widget, *_):
            outline.rounded_rectangle = (widget.x, widget.y, widget.width, widget.height, widget.height/2)
        button.bind(pos=paint, size=paint)
        paint(button)

    def build_detail_layout(self):
        """Design 02/2b order: price hero, plain status, chart, ranges, lines, signals, backtest."""
        from .app import Panel, WrappedLabel, LabButton
        from kivy.uix.scrollview import ScrollView
        from .widgets import ChipSelector
        # Header: Back · security and line (opens the saved-lines sheet) · Save.
        bar = self.saved_menu_label.parent
        bar.clear_widgets()
        self.detail_back_button = IconButton(kind='back', pos_hint={'center_y': .5})
        self.detail_back_button.bind(on_release=self.leave_detail)
        bar.add_widget(self.detail_back_button)
        self.saved_menu_label.fill = BG
        self.saved_menu_label.halign = 'center'
        self.saved_menu_label.font_size = sp(14)
        self.saved_menu_label.bind(size=lambda widget, _: setattr(widget, 'text_size', (widget.width-dp(8), None)))
        self.saved_menu_label.shorten = True
        bar.add_widget(self.saved_menu_label)
        self.save_button.parent.remove_widget(self.save_button)
        self.save_button.fill = BG
        self.save_button.color = ACCENT
        self.save_button.font_size = sp(14)
        self.save_button.width = dp(72)
        self.save_button._draw()
        bar.add_widget(self.save_button)
        # Hero: identity, large latest close and the visible-range change.
        content = self.content
        # Widgets below the old detail panels (e.g. the research footnote) stay below.
        below = len(content.children[:content.children.index(self.table_panel)])
        for widget in (self.optimal_panel, self.plot_panel, self.inline_lines, self.cards, self.table_panel):
            if widget.parent is not None:
                widget.parent.remove_widget(widget)
        self.plot_panel.remove_widget(self.plot_header)
        self.plot_panel.remove_widget(self.chart_change)
        self.plot_panel.remove_widget(self.timeline_selector)
        self.detail_hero = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        self.detail_hero.bind(minimum_height=self.detail_hero.setter('height'))
        self.detail_hero.add_widget(self.plot_header)
        self.detail_price = WrappedLabel(text='—', bold=True, font_size=sp(34))
        self.detail_hero.add_widget(self.detail_price)
        self.detail_hero.add_widget(self.chart_change)
        # Plain-language status before numbers.
        self.detail_status = Panel()
        self.detail_summary = WrappedLabel(text='', font_size=sp(19), bold=True)
        self.detail_note = WrappedLabel(text='', color=MUTED, font_size=sp(16))
        self.detail_status.add_widget(self.detail_summary)
        self.detail_status.add_widget(self.detail_note)
        # Range chips under the chart; scroll sideways only when 44 dp chips cannot fit.
        old_selector = self.timeline_selector
        self.timeline_selector = ChipSelector(old_selector.values or ('1Y',), text=old_selector.text,
                                              size_hint_x=None, spacing=dp(4))
        self.timeline_selector.bind(on_select=lambda _, value: self.chart.set_timeline(value))
        self.timeline_strip = ScrollView(do_scroll_y=False, size_hint_y=None, height=dp(44), bar_width=0)
        self.timeline_strip.add_widget(self.timeline_selector)
        def fit_ranges(*_):
            count = max(1, len(self.timeline_selector.values))
            self.timeline_selector.width = max(self.timeline_strip.width, count*dp(44) + (count-1)*dp(4))
        self.timeline_strip.bind(width=fit_ranges)
        self.timeline_selector.bind(children=fit_ranges)
        # Signals per year: the same validated target as the builder, plus the primary action.
        self.detail_signals = Panel()
        self.detail_signals.add_widget(WrappedLabel(text='SIGNALS PER YEAR', color=MUTED, bold=True, font_size=sp(12)))
        chips = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        self.detail_frequency_buttons = {}
        for value in (4, 6, 12, 'Custom'):
            button = LabButton(text=str(value))
            button.bind(on_release=lambda _, value=value: self.choose_detail_frequency(value))
            self.detail_frequency_buttons[value] = button
            chips.add_widget(button)
        self.detail_signals.add_widget(chips)
        self.detail_optimize_button = LabButton(text='', primary=True)
        self.detail_optimize_button.height = dp(52)
        self.detail_optimize_button.font_size = sp(15)
        self.detail_optimize_button.halign = 'center'
        self.detail_optimize_button.bind(on_release=self.on_detail_optimize,
            size=lambda button, _: setattr(button, 'text_size', (button.width-dp(16), None)))
        self.detail_optimize_note = WrappedLabel(text='Matches signal frequency, not profit.', color=MUTED,
                                                 font_size=sp(12), halign='center')
        for widget in ((self.detail_hero, self.detail_status, self.plot_panel, self.timeline_strip,
                                        self.inline_lines, self.optimal_panel, self.detail_signals,
                                        self.detail_optimize_button, self.detail_optimize_note, self.table_panel)):
            content.add_widget(widget, index=below)
        # The two frequency cards are summarized in the status card; keep their
        # values current (search/builder flows read them) without showing them.
        self.optimal_caption.text = 'SELECTED LINE'

    def leave_detail(self, *_):
        if len(self._page_stack) > 1:
            self.go_back()
        else:
            self.select_tab('library')

    def choose_detail_frequency(self, value):
        if value == 'Custom':
            self.target.text = 'Custom'
            self.show_parameters()
            return
        self.target.text = f'{value} / year'
        self.refresh_detail_frequency()

    def refresh_detail_frequency(self, *_):
        if not hasattr(self, 'detail_frequency_buttons'):
            return
        text = self.target.text
        for value, button in self.detail_frequency_buttons.items():
            selected = text == ('Custom' if value == 'Custom' else f'{value} / year')
            button.fill = ACCENT_TINT if selected else CONTROL
            button.color = ACCENT if selected else TEXT
            button._draw()
        try:
            target = int(text.split()[0]) if text != 'Custom' else self.model.target_frequency
        except ValueError:
            target = self.model.target_frequency
        self.detail_optimize_button.text = 'Calculating…' if self.busy else f'Find best SMA for {target} signals / year'
        self.detail_optimize_button.disabled = self.busy or (self.yahoo_enabled and not self.model.dataset.prices)

    def on_detail_optimize(self, *_):
        self._optimize_in_place = True
        try:
            self.on_optimize()
        finally:
            self._optimize_in_place = False

    def refresh_detail(self):
        from .chart_comparison import currency_prefix
        data, result = self.model.dataset, self.model.result
        security = self.model.security(data.counter) if data.prices else None
        ticker = security.ticker if security else ''
        self.saved_menu_label.text = (f'{ticker} · {self.model.current_line_name()}' if result and ticker
                                      else ticker or 'Saved lines')
        live = not getattr(data, 'is_simulated', True)
        price = next((value for value in reversed(data.prices) if value is not None), None) if data.prices else None
        self.detail_price.text = (f'{currency_prefix(getattr(data, "currency", "")) if live else "$"}{price:,.2f}'
                                  if price is not None else '—')
        if result is None:
            self.detail_summary.text = 'Choose a security and find your SMA line.'
            self.detail_note.text = ''
        else:
            state = line_state(data.prices, result.period).lower()
            self.detail_summary.text = f'Price is {state} its {result.period}-day line'
            last = result.events[-1] if result.events else None
            when = ''
            if last is not None:
                if live:
                    from datetime import date
                    day = date.fromisoformat(data.dates[last.index])
                    when = f'It crossed above on {day.day} {day:%b %Y}. '
                else:
                    when = f'It last crossed above on trading day {last.index + 1}. '
            self.detail_note.text = (when + f'This line has been crossed upward about '
                                     f'{result.actual_annual_frequency:.1f} times a year.')
        self.refresh_detail_frequency()

    def _settings_card(self, title):
        from .app import Panel, WrappedLabel
        card = Panel()
        card.add_widget(WrappedLabel(text=title, color=MUTED, bold=True, font_size=sp(12)))
        return card

    def _setting_row(self, button, value='', danger=False):
        """A full-width list row (design 04): title left, muted value and chevron right."""
        from .app import WrappedLabel
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        button.fill = SURFACE
        button.halign = 'left'
        button.bold = False
        button.font_size = sp(15)
        button.color = NEGATIVE if danger else TEXT
        button.bind(size=lambda widget, _: setattr(widget, 'text_size', (widget.width, None)))
        button._draw()
        row.add_widget(button)
        hint = WrappedLabel(text=(value + '  ›').strip(), color=MUTED, font_size=sp(12), halign='right',
                            size_hint_x=None, width=dp(140), pos_hint={'center_y': .5})
        row.add_widget(hint)
        return row

    def restructure_settings(self):
        """Design 04 cards; every existing control keeps its behaviour and name."""
        from .app import Panel, WrappedLabel
        from .notifications import signal_title
        from .version import APP_VERSION
        content = self.settings_content
        old_panels = list(content.children)
        appearance = self.appearance_panel
        for widget in old_panels:
            content.remove_widget(widget)
        # Notification types: the existing master switches, shorter copy.
        types = self._settings_card('NOTIFICATION TYPES')
        details = {
            'phone_buy': ('buy', 'Adjusted close crossed above a saved line. US 6:30 am, SG 6:30 pm SGT.'),
            'phone_monitor': ('monitor', 'Adjusted close is below a saved line. US 6:30 am, SG 6:30 pm SGT.'),
            'phone_monitor_start': ('monitor_start', 'Reminder before the open when the last close is above a '
                                                     'saved line. US 9:30 pm, SG 9:00 am SGT.'),
        }
        for key, (kind, description) in details.items():
            switch = self.notification_switches[key]
            if switch.parent is not None:
                switch.parent.remove_widget(switch)
            row = BoxLayout(size_hint_y=None, spacing=dp(8))
            words = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
            words.bind(minimum_height=words.setter('height'))
            words.add_widget(WrappedLabel(text=signal_title(kind), font_size=sp(15)))
            words.add_widget(WrappedLabel(text=description if self.yahoo_enabled else
                                          'Simulated data: tested manually below.', color=MUTED, font_size=sp(12)))
            words.bind(height=lambda _, height, row=row: setattr(row, 'height', max(dp(52), height)))
            row.add_widget(words)
            switch.pos_hint = {'center_y': .5}
            row.add_widget(switch)
            types.add_widget(row)
        types.add_widget(WrappedLabel(
            text='These are master switches for all saved lines; choose lines and types in Alerts. US closing checks '
                 'run Tuesday–Saturday, SGX Monday–Friday, opening reminders Monday–Friday, all in Singapore time. '
                 'Times are targets; your phone decides when background checks run.', color=MUTED, font_size=sp(12)))
        # Background check and test notifications.
        check = self._settings_card('BACKGROUND CHECK')
        check.add_widget(WrappedLabel(text='Sends a test through the same path as a real alert. No market data is requested.',
                                      color=MUTED, font_size=sp(13)))
        for button in (self.phone_test_button, getattr(self, 'background_test_button', None)):
            if button is None:
                continue
            if button.parent is not None:
                button.parent.remove_widget(button)
            button.fill = SURFACE
            button.color = ACCENT
            button._draw()
            check.add_widget(button)
        self.notification_status.parent.remove_widget(self.notification_status)
        check.add_widget(self.notification_status)
        # Simulated-data previews (desktop/demo only) keep their own card.
        preview = None
        leftovers = [widget for widget in list(self.settings_panel.children)[::-1]
                     if widget in (self.alert_session_label, self.preview_alert_button.parent,
                                   self.eod_deliver_button, self.alert_preview)]
        if leftovers:
            preview = self._settings_card('SIMULATED ALERT PREVIEW')
            for widget in leftovers:
                self.settings_panel.remove_widget(widget)
                preview.add_widget(widget)
        cards = [types, check] + ([preview] if preview else []) + [appearance]
        # Market data rows (live data only).
        if hasattr(self, 'api_status'):
            market = self._settings_card('MARKET DATA')
            for name, title, value, danger in (
                    ('api_check_button', 'Connection', 'Check', False),
                    ('api_refresh_button', 'Refresh prices', 'This security', False),
                    ('api_full_button', 'Refresh full history', 'This security', False),
                    ('api_log_button', 'Request log', 'View and copy', False),
                    ('api_clear_button', 'Clear downloaded data', 'Keeps saved SMAs', True)):
                button = getattr(self, name)
                if button.parent is not None:
                    button.parent.remove_widget(button)
                button.text = title
                market.add_widget(self._setting_row(button, value, danger))
                if name == 'api_check_button':
                    self.api_status.parent.remove_widget(self.api_status)
                    market.add_widget(self.api_status)
            cards.append(market)
        legal = self._settings_card('LEGAL')
        legal.add_widget(WrappedLabel(text='This app is for personal use only and is not financial advice. It does not '
                                           'guarantee profits or future performance. Past results do not predict future '
                                           'results, and you are responsible for your own investment decisions.',
                                      font_size=sp(14)))
        cards.append(legal)
        for card in cards:
            content.add_widget(card)
        self.version_label = WrappedLabel(text=f'Version {APP_VERSION}', color=MUTED, halign='center', font_size=sp(12))
        content.add_widget(self.version_label)
        self.settings_cards = dict(types=types, check=check, legal=legal)

    RECENT_KEY = 'recent_securities'

    def restructure_search(self):
        """Design 10/11: flat search, teal Search, recent securities and the guided example."""
        from .app import Panel, WrappedLabel, LabButton
        panel = self.search_panel
        panel._panel_color.rgba = BG
        panel.padding = (0, dp(4))
        panel.remove_widget(panel.children[-1])  # the old SEARCH SECURITY caption
        self.page_titles['search'].font_size = sp(24)
        self.search_submit.fill = ACCENT
        self.search_submit.color = ON_ACCENT
        self.search_submit.font_size = sp(15)
        self.search_submit.width = dp(96)
        self.search_submit._draw()
        row = self.security_search.parent
        row.height = dp(48)
        self.search_submit.height = dp(48)
        self.security_search.height = dp(48)
        if self.yahoo_enabled:
            self.search_status.text = ('Covers US and Singapore listed stocks and ETFs. '
                                       'Press Search or Enter to look up matches.')
        self.search_status.font_size = sp(13)
        # Recent securities: opened before, so their history is already downloaded.
        self.recent_panel = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        self.recent_panel.bind(minimum_height=self.recent_panel.setter('height'))
        panel.add_widget(self.recent_panel)
        self.guide_card = Panel()
        words = BoxLayout(orientation='horizontal', size_hint_y=None, spacing=dp(10))
        text = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        text.bind(minimum_height=text.setter('height'))
        text.add_widget(WrappedLabel(text='New to moving averages?', bold=True, font_size=sp(15)))
        text.add_widget(WrappedLabel(text='Walk through an example on Vanguard S&P 500 ETF.' if self.yahoo_enabled
                                     else 'Walk through an educational example.', color=MUTED, font_size=sp(13)))
        text.bind(height=lambda _, height: setattr(words, 'height', max(dp(48), height)))
        words.add_widget(text)
        self.guide_start_button = LabButton(text='Start', size_hint_x=None, width=dp(80), pos_hint={'center_y': .5})
        self.guide_start_button.color = ACCENT
        self.guide_start_button.bind(on_release=self.show_guide)
        words.add_widget(self.guide_start_button)
        self.guide_card.add_widget(words)
        panel.add_widget(self.guide_card)
        self.security_search.bind(text=lambda *_: self.refresh_recent())
        self.refresh_recent()

    def show_search_error(self, detail):
        """Design 14: a calm, retryable card. Saved lines and cached charts keep working."""
        from .app import Panel, WrappedLabel, LabButton
        from .theme import NEGATIVE_TINT
        card = getattr(self, 'search_error_card', None)
        if card is None:
            card = self.search_error_card = Panel()
            card._panel_color.rgba = NEGATIVE_TINT
            card.add_widget(WrappedLabel(text='Search is unavailable right now', bold=True, color=NEGATIVE,
                                         font_size=sp(16)))
            self.search_error_detail = WrappedLabel(text='', color=TEXT, font_size=sp(14))
            card.add_widget(self.search_error_detail)
            card.add_widget(WrappedLabel(text='Your saved lines and cached charts still work. Wait a minute, then try again.',
                                         color=MUTED, font_size=sp(13)))
            self.search_retry_button = LabButton(text='Try again', size_hint_x=None, width=dp(120))
            self.search_retry_button.fill = NEGATIVE_TINT
            self.search_retry_button._draw()
            self.search_retry_button.bind(on_release=lambda *_: self.submit_security_search())
            card.add_widget(self.search_retry_button)
        self.search_error_detail.text = detail
        if card.parent is None:
            panel = self.search_panel
            panel.add_widget(card, index=panel.children.index(self.search_status))

    def recent_keys(self):
        import json
        with self.model.store._connect() as db:
            row = db.execute("SELECT value FROM preferences WHERE key=?", (self.RECENT_KEY,)).fetchone()
        try:
            keys = json.loads(row[0]) if row else []
        except ValueError:
            keys = []
        return [key for key in keys if isinstance(key, str)]

    def remember_recent(self, key):
        import json
        keys = [key] + [item for item in self.recent_keys() if item != key]
        with self.model.store._connect() as db:
            db.execute("INSERT OR REPLACE INTO preferences VALUES (?,?)", (self.RECENT_KEY, json.dumps(keys[:6])))

    def clear_recent(self, *_):
        with self.model.store._connect() as db:
            db.execute("DELETE FROM preferences WHERE key=?", (self.RECENT_KEY,))
        self.refresh_recent()

    def refresh_recent(self):
        from .app import WrappedLabel, LabButton
        from .widgets import SecurityMatchButton
        if not hasattr(self, 'recent_panel'):
            return
        self.recent_panel.clear_widgets()
        self.recent_buttons = []
        # Only before a search: results replace the recent list.
        idle = not (self.security_match_buttons or self.security_search.text.strip())
        if idle and self.guide_card.parent is None:
            self.search_panel.add_widget(self.guide_card)
        elif not idle and self.guide_card.parent is not None:
            self.guide_card.parent.remove_widget(self.guide_card)
        if not idle:
            return
        counts = {}
        for line in self.model.library_lines():
            counts[line.counter] = counts.get(line.counter, 0) + 1
        securities = []
        for key in self.recent_keys():
            try:
                securities.append(self.model.security(key))
            except (KeyError, ValueError):
                continue
        if not securities:
            return
        header = BoxLayout(size_hint_y=None, height=dp(44))
        header.add_widget(WrappedLabel(text='RECENT', color=MUTED, bold=True, font_size=sp(12), pos_hint={'center_y': .5}))
        clear = LabButton(text='Clear', size_hint_x=None, width=dp(72), pos_hint={'center_y': .5})
        clear.fill = BG
        clear._draw()
        clear.bind(on_release=self.clear_recent)
        header.add_widget(clear)
        self.recent_clear_button = clear
        self.recent_panel.add_widget(header)
        for security in securities:
            count = counts.get(security.key, 0)
            button = SecurityMatchButton(security, action=(f'{count} saved line' + ('s' if count != 1 else ''))
                                         if count else 'No lines yet', action_muted=True)
            button.bind(on_release=lambda _, item=security: self.open_recent(item))
            self.recent_buttons.append(button)
            self.recent_panel.add_widget(button)

    def open_recent(self, security):
        # Same validated selection path as a search match (cached history first).
        self.search_results = (security,)
        self.select_security_match(security)

    def select_tab(self, destination):
        if self.busy:
            self.cancel_optimization()
        if destination == 'library':
            self.show_library()
        else:
            self._navigate(destination)
        if destination == 'alerts':
            self.refresh_alerts()

    def refresh_frequency_chips(self, *_):
        for value, button in self.frequency_buttons.items():
            selected = self.target.text == ('Custom' if value == 'Custom' else f'{value} / year')
            button.fill = (.06,.23,.21,1) if selected else CONTROL
            button.color = ACCENT if selected else TEXT
            button._draw()

    def layout_tabs(self, *_):
        if not hasattr(self, 'tab_bar'):
            return
        height = 0 if any(editor.focus for editor in self.editors) else dp(58)
        self.tab_bar.height = height
        self.tab_bar.opacity = 1 if height else 0
        self.tab_bar.disabled = not bool(height)
        self.manager.size_hint = (None, None)
        self.manager.pos_hint = {}
        self.manager.pos = (self.x, self.y + height)
        self.manager.size = (self.width, max(0, self.height-height))
        self.alerts_scroll.width = min(self.width, dp(1000))

    def update_tabs(self, *_):
        if not hasattr(self,'tab_buttons'):
            return
        current = self.manager.current
        if current in ('search','crossovers','guide'):
            current = 'results'
        for key, button in self.tab_buttons.items():
            button.color = ACCENT if key == current else MUTED
            button.fill = BG
            button._draw()

    def refresh_alerts(self):
        from .app import Panel, WrappedLabel, LabButton
        from .notifications import signal_title
        self.alerts_content.clear_widgets()
        self.alert_switches = {}
        settings = self.model.store.notification_settings()
        globally_on = {'buy': settings.phone_buy, 'monitor': settings.phone_monitor,
                       'monitor_start': settings.phone_monitor_start}
        self.alerts_content.add_widget(WrappedLabel(text='Choose which saved lines can notify you, and which signal types each line sends. '
                                                         'Schedules and the master switch for each type are in Settings.',color=MUTED))
        for line in self.model.library_lines():
            panel = Panel()
            panel.add_widget(WrappedLabel(text=f'{self.model.security(line.counter).ticker} · {line.display_name}',bold=True,font_size=sp(17)))
            row = BoxLayout(size_hint_y=None,height=dp(48))
            row.add_widget(WrappedLabel(text='Phone alerts',pos_hint={'center_y':.5},bold=True))
            switch = RuleSwitch(active=line.push_enabled)
            switch.bind(active=lambda _, enabled, item=line: self.on_line_alert(item,'phone'))
            row.add_widget(switch)
            panel.add_widget(row)
            self.alert_switches[(line.id,'phone')] = switch
            for kind in ('buy','monitor','monitor_start'):
                row = BoxLayout(size_hint_y=None,height=dp(48),padding=(dp(12),0,0,0))
                note = '' if globally_on[kind] else '\nOff for all lines in Settings'
                row.add_widget(WrappedLabel(text=signal_title(kind)+note,pos_hint={'center_y':.5},
                    color=TEXT if line.push_enabled and globally_on[kind] else MUTED,font_size=sp(13)))
                type_switch = RuleSwitch(active=line.alert_enabled(kind))
                type_switch.disabled = not line.push_enabled
                type_switch.opacity = 1 if line.push_enabled else .45
                type_switch.bind(active=lambda _, enabled, item=line, kind=kind: self.on_line_signal_type(item,kind,enabled))
                row.add_widget(type_switch)
                panel.add_widget(row)
                self.alert_switches[(line.id,kind)] = type_switch
            panel.add_widget(WrappedLabel(text='Turn on Phone alerts to choose signal types. Hidden lines can still send alerts.'
                                          if not line.push_enabled else 'Hidden lines can still send alerts.',color=MUTED))
            self.alerts_content.add_widget(panel)
        if not self.model.library_lines():
            self.alerts_content.add_widget(WrappedLabel(text='Save an SMA line to set up alerts.',font_size=sp(20)))
        settings = LabButton(text='Notification settings')
        settings.bind(on_release=self.show_settings)
        self.alerts_content.add_widget(settings)

    def on_line_signal_type(self, line, kind, enabled):
        try:
            self.model.store.set_line_alert(line.id, kind, enabled)
        except (ValueError, sqlite3.Error) as error:
            self.message(str(error), True)
        self.refresh()
        self.sync_notification_schedule()

    def populate_home(self, panel):
        from .app import WrappedLabel, LabButton
        from .widgets import LegendSymbol
        from .palette import line_color
        panel.clear_widgets()
        panel.padding=0
        panel._panel_color.rgba=BG
        cards = watchlist(self.model)
        below = sum(card['below'] for card in cards)
        above = sum(state == 'Above' for card in cards for state in card['states'].values())
        self.home_summary_caption.text = f'Saved SMAs · {above} above line' if cards else ''
        self.home_summary_title.text = ((f'{below} impending buy' + ('' if below == 1 else 's')) if below
                                        else 'No impending buys') if cards else 'Your watchlist starts here'
        first = next(((card, line) for card in cards for line in card['lines'] if card['states'][line.id] == 'Below'), None)
        self.home_summary_note.text = (f"{first[0]['security'].name} is below its {first[1].period}-day line."
                                       if first else 'Every saved security is at or above its lines.' if cards
                                       else 'Based on downloaded adjusted closes.')
        header = BoxLayout(size_hint_y=None,height=dp(44))
        header.add_widget(WrappedLabel(text='WATCHLIST',color=MUTED,bold=True))
        self.landing_history_button = LabButton(text='Archive',size_hint_x=None,width=dp(90))
        self.landing_history_button.bind(on_release=self.open_unsaved_history)
        header.add_widget(self.landing_history_button)
        panel.add_widget(header)
        rows, groups, buttons = {}, {}, {}
        for card in cards:
            security, counter = card['security'], card['counter']
            expanded = counter in self.expanded_saved_securities
            group = SavedSecurityGroup(expanded=expanded)
            heading = BoxLayout(size_hint_y=None,height=dp(58),spacing=dp(4))
            name = SecurityIdentityButton(text=counter,show_ticker=True,stacked=True,pos_hint={'center_y':.5})
            name.set_security(security)
            name.font_size = sp(17)
            name.height = dp(52)
            if name.ticker_label is not None:
                name.ticker_label.font_size = sp(12)
            name.bind(on_release=lambda _, key=counter:self.toggle_saved_security(key))
            heading.add_widget(name)
            quote = BoxLayout(orientation='vertical',size_hint_x=.6,spacing=dp(2))
            quote.add_widget(WrappedLabel(text=(f"${card['price']:,.2f}" if card['price'] is not None else 'No cached close'),
                                 bold=True,halign='right',font_size=sp(16)))
            change=card['change']
            change_box = AnchorLayout(anchor_x='right', size_hint_y=None, height=dp(22))
            if change is None:
                change_box.add_widget(WrappedLabel(text='Change unavailable', color=MUTED, halign='right', font_size=sp(12)))
            else:
                direction = 'up' if change > 0 else 'down' if change < 0 else 'flat'
                value = ChangeValue()
                value.value_label.font_size = sp(13)
                value.show(f'{abs(change):.1f}%', direction,
                           NEGATIVE if change < 0 else ACCENT if change > 0 else MUTED)
                change_box.add_widget(value)
            quote.add_widget(change_box)
            heading.add_widget(quote)
            group.add_widget(heading)
            summary = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
            count = len(card['lines'])
            states = set(card['states'].values())
            state = (f"{card['below']} OF {count} LINE{'S' if count != 1 else ''} BELOW" if card['below']
                     else ('ABOVE BOTH LINES' if count == 2 else 'ABOVE ALL LINES' if count > 2 else 'ABOVE LINE')
                     if states == {'Above'} else ' · '.join(sorted(states)).upper())
            summary.add_widget(Pill(text=state, negative=bool(card['below']), pos_hint={'center_y': .5}))
            summary.add_widget(Label())
            arrow = LinesToggle(count, expanded=expanded, pos_hint={'center_y': .5})
            arrow.bind(on_release=lambda _,key=counter:self.toggle_saved_security(key))
            summary.add_widget(arrow)
            group.add_widget(summary)
            body = BoxLayout(orientation='vertical',size_hint_y=None,spacing=dp(8))
            body.bind(minimum_height=body.setter('height'))
            for line in card['lines']:
                row=BoxLayout(size_hint_y=None,height=dp(64),spacing=dp(8))
                view=SavedLineRow(line.display_name,
                    f'{line.target_frequency} signals / year · Alert '+('on' if line.push_enabled else 'off'),
                    line_color(self.model.store.color_index(line.counter,line.scenario,line.period)),
                    pos_hint={'center_y':.5})
                view.bind(height=lambda widget,height,row=row:setattr(row,'height',max(dp(56),height)))
                view.bind(on_release=lambda _,line=line:self.on_view_saved(line))
                swatch=view.swatch
                row.add_widget(view)
                state_label=Pill(text=card['states'][line.id].upper(),negative=card['states'][line.id]=='Below',
                    pos_hint={'center_y':.5})
                row.add_widget(state_label)
                body.add_widget(row)
                rows[line.id]={'view':view,'title':view.name_label,'state':state_label,'swatch':swatch}
            reveal = PreferenceReveal(body,detach_when_hidden=True)
            group.add_widget(reveal)
            reveal.show(expanded)
            panel.add_widget(group)
            groups[counter] = dict(group=group,body=body,name=name,reveal=reveal)
            buttons[counter] = arrow
        self.landing_security_groups, self.landing_security_buttons = groups, buttons
        return rows

    def refresh_experience(self):
        if not hasattr(self,'detail_summary'):
            return
        self.save_button.text = 'Saved' if self.model.current_saved_line() else 'Save'
        self.refresh_detail()
        self.refresh_alerts()
        self.refresh_inline_lines()

    def refresh_inline_lines(self):
        from .app import WrappedLabel, LabButton
        from .widgets import LegendSymbol
        from .palette import line_color
        self.inline_lines.clear_widgets()
        lines=self.model.store.list_lines(self.model.dataset.counter,self.model.dataset.scenario)
        if not lines:
            self.inline_lines.height=0
            self.inline_lines.opacity=0
            self.inline_lines.padding=0
            return
        self.inline_lines.opacity=1
        self.inline_lines.padding=dp(14)
        self.inline_lines.add_widget(WrappedLabel(text=f'SAVED LINES · {sum(line.visible for line in lines)} OF {len(lines)} SHOWN',color=MUTED,bold=True))
        for line in lines:
            row=BoxLayout(size_hint_y=None,height=dp(76),spacing=dp(6))
            row.add_widget(LegendSymbol(line_color(self.model.store.color_index(line.counter,line.scenario,line.period)),pos_hint={'center_y':.5}))
            name=WrappedLabel(text=f'{line.display_name}\n{line.target_frequency} signals / year',pos_hint={'center_y':.5})
            row.add_widget(name)
            edit=LabButton(text='Edit',size_hint_x=None,width=dp(48),pos_hint={'center_y':.5})
            def edit_line(_,line=line):
                self.show_rename_line(line=line)
            edit.bind(on_release=edit_line)
            row.add_widget(edit)
            switch=RuleSwitch(active=line.visible,pos_hint={'center_y':.5})
            switch.bind(active=lambda _,enabled,line=line:self.on_saved_visibility(line))
            row.add_widget(switch)
            self.inline_lines.add_widget(row)
        self.inline_lines.add_widget(WrappedLabel(text='The switch shows or hides a line. Hidden lines can still send alerts.',color=MUTED))

    def build_signup(self):
        """Expose opt-in signup only after the configured server advertises it."""
        from .contact import base_url, capabilities
        if not base_url():
            return
        future = self.market_executor.submit(capabilities)
        future.add_done_callback(lambda result: Clock.schedule_once(lambda _: self.signup_ready(result),0))

    def build_appearance(self):
        import json
        from .app import Panel, WrappedLabel, LabButton
        from .appearance import set_mode
        with self.model.store._connect() as db:
            row=db.execute("SELECT value FROM preferences WHERE key='appearance'").fetchone()
        mode=json.loads(row[0]) if row else 'dark'
        set_mode(mode)
        panel=Panel()
        panel.add_widget(WrappedLabel(text='APPEARANCE',bold=True,color=MUTED,font_size=sp(12)))
        buttons=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(8))
        self.appearance_buttons={}
        def select(mode):
            with self.model.store._connect() as db:
                db.execute("INSERT OR REPLACE INTO preferences VALUES ('appearance',?)",(json.dumps(mode),))
            set_mode(mode)
            for key,button in self.appearance_buttons.items():
                button.color=ACCENT if key==mode else TEXT
                button.fill=ACCENT_TINT if key==mode else CONTROL
                button._draw()
        for key in ('system','light','dark'):
            button=LabButton(text=key.title())
            button.color=ACCENT if key==mode else TEXT
            button.fill=ACCENT_TINT if key==mode else CONTROL
            button._draw()
            button.bind(on_release=lambda _,key=key:select(key))
            buttons.add_widget(button)
            self.appearance_buttons[key]=button
        panel.add_widget(buttons)
        self.settings_content.add_widget(panel)
        self.appearance_panel=panel

    def signup_ready(self,future):
        from .app import Panel, WrappedLabel, LabButton, EditingField
        import json
        try:
            if self.closed or not future.result(): return
        except Exception:
            return
        panel=Panel()
        panel.add_widget(WrappedLabel(text='YOUR EMAIL',bold=True,color=MUTED,font_size=sp(12)))
        self.contact_editor=EditingField(multiline=False,hint_text='name@example.com',font_size=sp(16),
             size_hint_y=None,height=dp(48),background_normal='',background_color=CONTROL,foreground_color=TEXT)
        with self.model.store._connect() as db:
            row=db.execute("SELECT value FROM preferences WHERE key='release_contact_email'").fetchone()
        self.contact_editor.text=json.loads(row[0]) if row else ''
        entry=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(8))
        entry.add_widget(self.contact_editor)
        self.contact_submit=LabButton(text='Save',primary=True,size_hint_x=None,width=dp(84))
        self.contact_submit.height=dp(48)
        self.contact_submit.bind(on_release=self.submit_contact)
        entry.add_widget(self.contact_submit)
        panel.add_widget(entry)
        panel.add_widget(WrappedLabel(text='Optional. Used only to send you release updates from the developer. '
                                           'Voluntary signups are counted; this is not a total download count.',
                                      color=MUTED,font_size=sp(12)))
        self.contact_status=WrappedLabel(text='',color=MUTED)
        panel.add_widget(self.contact_status)
        self.settings_content.add_widget(panel,index=len(self.settings_content.children))
        # A dismissible first-open invitation leaves the app fully usable.
        with self.model.store._connect() as db:
            seen=db.execute("SELECT value FROM preferences WHERE key='release_contact_seen'").fetchone()
        if not seen:
            self.show_welcome()

    def show_welcome(self):
        """Design 06: optional email on first open, with Skip for now."""
        from .app import ScreenPopup, WrappedLabel, LabButton, EditingField, Panel
        from kivy.uix.image import Image
        from kivy.uix.scrollview import ScrollView
        from pathlib import Path
        from .notifications import validate_email
        body = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(14), padding=(dp(24), dp(32), dp(24), dp(24)))
        body.bind(minimum_height=body.setter('height'))
        icon = Image(source=str(Path(__file__).parent/'assets/app-icon.png'), size_hint=(None, None),
                     size=(dp(56), dp(56)), fit_mode='contain')
        body.add_widget(icon)
        body.add_widget(WrappedLabel(text='Welcome to SMA Stock Analyzer', bold=True, font_size=sp(26)))
        body.add_widget(WrappedLabel(text='Before you start, you can leave your email. This is all it is used for.',
                                     color=MUTED, font_size=sp(15)))
        points = Panel()
        for title, detail in (('Release updates', 'The developer emails you when a new version is ready.'),
                              ('A signup count', 'It shows how many people chose to sign up.'),
                              ('Nothing else', 'Your email is not used for any other purpose.')):
            points.add_widget(WrappedLabel(text='•  ' + title, bold=True, font_size=sp(15)))
            points.add_widget(WrappedLabel(text=detail, color=MUTED, font_size=sp(13)))
        body.add_widget(points)
        body.add_widget(WrappedLabel(text='Email address', font_size=sp(14)))
        self.welcome_editor = EditingField(multiline=False, hint_text='name@example.com', font_size=sp(16),
            size_hint_y=None, height=dp(52), background_normal='', background_active='',
            background_color=BG, foreground_color=TEXT)
        body.add_widget(self.welcome_editor)
        self.welcome_status = WrappedLabel(text='', color=NEGATIVE, font_size=sp(13))
        body.add_widget(self.welcome_status)
        self.welcome_continue = LabButton(text='Continue', primary=True)
        self.welcome_continue.height = dp(52)
        self.welcome_continue.font_size = sp(16)
        body.add_widget(self.welcome_continue)
        self.welcome_skip = LabButton(text='Skip for now')
        self.welcome_skip.fill = BG
        self.welcome_skip.font_size = sp(15)
        self.welcome_skip._draw()
        body.add_widget(self.welcome_skip)
        body.add_widget(WrappedLabel(text='You can add or change your email later in Settings.', color=MUTED,
                                     font_size=sp(12), halign='center'))
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(body)
        popup = ScreenPopup(self, title='', title_size=0, separator_height=0, content=scroll, size_hint=(1, 1),
                            background='', background_color=BG, auto_dismiss=False)
        self.welcome_popup = popup
        def done(*_):
            with self.model.store._connect() as db:
                db.execute("INSERT OR REPLACE INTO preferences VALUES ('release_contact_seen','true')")
            self.welcome_editor.focus = False
            popup.dismiss()
        def proceed(*_):
            try:
                email = validate_email(self.welcome_editor.text)
            except ValueError as error:
                self.welcome_status.text = str(error)
                return
            if not email:
                self.welcome_status.text = 'Enter your email, or choose Skip for now.'
                return
            self.contact_editor.text = email
            self.submit_contact()
            done()
        self.welcome_skip.bind(on_release=done)
        self.welcome_continue.bind(on_release=proceed)
        self.welcome_editor.bind(on_text_validate=proceed)
        popup.open()

    def submit_contact(self,*_):
        import uuid,json
        from .contact import submit
        with self.model.store._connect() as db:
            row=db.execute("SELECT value FROM preferences WHERE key='release_install_id'").fetchone()
            identifier=json.loads(row[0]) if row else str(uuid.uuid4())
            db.execute("INSERT OR REPLACE INTO preferences VALUES ('release_install_id',?)",(json.dumps(identifier),))
        self.contact_submit.disabled=True
        self.contact_status.text='Sending…'
        future=self.market_executor.submit(submit,self.contact_editor.text,identifier)
        def finish(_):
            if self.closed:return
            self.contact_submit.disabled=False
            try:
                email=future.result()
                with self.model.store._connect() as db:
                    db.execute("INSERT OR REPLACE INTO preferences VALUES ('release_contact_email',?)",(json.dumps(email),))
                self.contact_status.text='Email sent to the developer.'
            except ValueError as error:self.contact_status.text=str(error)
            except Exception:self.contact_status.text='Email was not sent. Check your connection and try again.'
        future.add_done_callback(lambda _:Clock.schedule_once(finish,0))
