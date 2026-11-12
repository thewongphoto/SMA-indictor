"""Four-tab presentation layered over the existing calculation and data flows."""
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from .theme import ACCENT, BG, SURFACE, CONTROL, MUTED, TEXT, NEGATIVE
from .widgets import SecurityIdentityButton, RuleSwitch, PreferenceReveal, IconButton, SavedSecurityGroup
from .watchlist import watchlist, line_state
from kivy.clock import Clock


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
        self.bind(size=self.layout_tabs, pos=self.layout_tabs)
        self.manager.bind(current=self.update_tabs)
        self.page_titles['library'].text = 'Home'
        self.page_titles['library'].font_size = sp(28)
        self.page_titles['search'].text = 'Find a security'
        self.new_analysis_button.text = '+ Find SMA'
        self.new_analysis_button.size_hint_x=None
        self.new_analysis_button.width=dp(112)
        self.new_analysis_button.fill=BG
        self.new_analysis_button.color=ACCENT
        self.page_titles['library'].parent.add_widget(self.new_analysis_button)
        self.search_submit.text = 'Search'
        self.security_search.hint_text = 'Company name or ticker'
        self.security_search.font_size = sp(16)
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
        self.refresh_frequency_chips()
        self.optimize_button.bind(size=lambda button, _: setattr(button, 'text_size', (button.width-dp(16), None)))
        self.home_summary = Panel()
        self.home_summary_title = WrappedLabel(text='Your saved lines', bold=True, font_size=sp(23))
        self.home_summary_note = WrappedLabel(text='', color=MUTED)
        self.home_summary.add_widget(self.home_summary_title)
        self.home_summary.add_widget(self.home_summary_note)
        self.detail_summary = WrappedLabel(text='', font_size=sp(16), bold=True)
        self.optimal_panel.add_widget(self.detail_summary)
        self.inline_lines = Panel()
        self.content.add_widget(self.inline_lines, index=self.content.children.index(self.plot_panel))
        self.library_intro.children[-1].text = 'No saved SMA lines yet'
        self.library_intro.children[-2].text = 'Find a stock or ETF, choose a signal frequency, and save the line.'
        find=LabButton(text='Find a security',primary=True)
        find.bind(on_release=self.show_search)
        self.library_intro.add_widget(find,index=1)
        legal = Panel()
        legal.add_widget(WrappedLabel(text='ABOUT THIS APP', color=MUTED, bold=True))
        legal.add_widget(WrappedLabel(text='For personal research. This app is not financial advice and does not guarantee profits. Past results do not predict future performance. You are responsible for your investment decisions.'))
        legal.add_widget(WrappedLabel(text=f'Version {__import__("sma_analyzer.version",fromlist=["APP_VERSION"]).APP_VERSION}', color=MUTED))
        self.settings_content.add_widget(legal)
        self.build_appearance()
        self.build_signup()
        self.layout_tabs()
        self.update_tabs()

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
        self.alerts_content.clear_widgets()
        self.alerts_content.add_widget(WrappedLabel(text='Choose which saved lines can notify you. Signal types and schedules are managed in Settings.',color=MUTED))
        for line in self.model.library_lines():
            panel = Panel()
            panel.add_widget(WrappedLabel(text=f'{self.model.security(line.counter).ticker} · {line.display_name}',bold=True,font_size=sp(17)))
            row = BoxLayout(size_hint_y=None,height=dp(48))
            row.add_widget(WrappedLabel(text='Phone alerts',pos_hint={'center_y':.5}))
            switch = RuleSwitch(active=line.push_enabled)
            switch.bind(active=lambda _, enabled, item=line: self.on_line_alert(item,'phone'))
            row.add_widget(switch)
            panel.add_widget(row)
            panel.add_widget(WrappedLabel(text='Uses the three enabled signal types and Singapore-time schedules. Hidden lines can still send alerts.',color=MUTED))
            self.alerts_content.add_widget(panel)
        if not self.model.library_lines():
            self.alerts_content.add_widget(WrappedLabel(text='Save an SMA line to set up alerts.',font_size=sp(20)))
        settings = LabButton(text='Notification settings')
        settings.bind(on_release=self.show_settings)
        self.alerts_content.add_widget(settings)

    def populate_home(self, panel):
        from .app import WrappedLabel, LabButton
        from .widgets import LegendSymbol
        from .palette import line_color
        panel.clear_widgets()
        panel.padding=0
        panel._panel_color.rgba=BG
        cards = watchlist(self.model)
        below = sum(card['below'] for card in cards)
        self.home_summary_title.text = (f'{below} '+('line needs attention' if below == 1 else 'lines need attention') if below else 'Your saved lines at a glance') if cards else 'Your watchlist starts here'
        self.home_summary_note.text = 'Based on downloaded adjusted closes. Expand a company to view its saved lines.'
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
            name.bind(on_release=lambda _, key=counter:self.toggle_saved_security(key))
            heading.add_widget(name)
            quote = BoxLayout(orientation='vertical',size_hint_x=.6)
            quote.add_widget(WrappedLabel(text=(f"{card['currency']} {card['price']:,.2f}" if card['price'] is not None else 'No cached close'),
                                 bold=True,halign='right',font_size=sp(16)))
            change=card['change']
            quote.add_widget(WrappedLabel(text=(f'{change:+.1f}%' if change is not None else 'Change unavailable'),
                color=NEGATIVE if change is not None and change<0 else ACCENT,halign='right',font_size=sp(12)))
            heading.add_widget(quote)
            group.add_widget(heading)
            summary = BoxLayout(size_hint_y=None,height=dp(44))
            state = f"{card['below']} OF {len(card['lines'])} LINES BELOW" if card['below'] else ' · '.join(sorted(set(card['states'].values()))).upper()
            summary.add_widget(WrappedLabel(text=state,color=NEGATIVE if card['below'] else ACCENT,bold=True,font_size=sp(12)))
            arrow = IconButton(kind='up' if expanded else 'down')
            arrow.bind(on_release=lambda _,key=counter:self.toggle_saved_security(key))
            summary.add_widget(WrappedLabel(text=f"{len(card['lines'])} saved lines",color=MUTED,halign='right'))
            summary.add_widget(arrow)
            group.add_widget(summary)
            body = BoxLayout(orientation='vertical',size_hint_y=None,spacing=dp(8))
            body.bind(minimum_height=body.setter('height'))
            for line in card['lines']:
                row=BoxLayout(size_hint_y=None,height=dp(72),spacing=dp(6))
                swatch=LegendSymbol(line_color(self.model.store.color_index(line.counter,line.scenario,line.period)))
                row.add_widget(swatch)
                view=LabButton(text=f'{line.display_name}\n{line.target_frequency} signals / year · Alert '+('on' if line.push_enabled else 'off'),
                    halign='left',pos_hint={'center_y':.5})
                view.fill=SURFACE
                view.bind(size=lambda widget,_:setattr(widget,'text_size',(widget.width-dp(4),None)))
                def fit_row(widget,size,row=row):
                    widget.height=max(dp(48),size[1]+dp(8))
                    row.height=widget.height+dp(8)
                view.bind(texture_size=fit_row)
                view.bind(on_release=lambda _,line=line:self.on_view_saved(line))
                row.add_widget(view)
                state_label=WrappedLabel(text=card['states'][line.id].upper(),color=NEGATIVE if card['states'][line.id]=='Below' else ACCENT,
                    font_size=sp(11),size_hint_x=None,width=dp(62),halign='right',pos_hint={'center_y':.5})
                row.add_widget(state_label)
                body.add_widget(row)
                rows[line.id]={'view':view,'title':view,'state':state_label,'swatch':swatch}
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
        result = self.model.result
        self.detail_summary.text = (f'Price is {line_state(self.model.dataset.prices,result.period).lower()} its {result.period}-day line.\n'
                                    f'About {result.actual_annual_frequency:.2f} upward crossings per year.' if result else 'Choose a security and find your SMA line.')
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
            row.add_widget(LegendSymbol(line_color(self.model.store.color_index(line.counter,line.scenario,line.period))))
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
        panel.add_widget(WrappedLabel(text='APPEARANCE',bold=True,color=MUTED))
        buttons=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(8))
        self.appearance_buttons={}
        def select(mode):
            with self.model.store._connect() as db:
                db.execute("INSERT OR REPLACE INTO preferences VALUES ('appearance',?)",(json.dumps(mode),))
            set_mode(mode)
            for key,button in self.appearance_buttons.items():
                button.color=ACCENT if key==mode else TEXT
        for key in ('system','light','dark'):
            button=LabButton(text=key.title())
            button.color=ACCENT if key==mode else TEXT
            button.bind(on_release=lambda _,key=key:select(key))
            buttons.add_widget(button)
            self.appearance_buttons[key]=button
        panel.add_widget(buttons)
        self.settings_content.add_widget(panel,index=1)

    def signup_ready(self,future):
        from .app import Panel, WrappedLabel, LabButton, EditingField
        import json
        try:
            if self.closed or not future.result(): return
        except Exception:
            return
        panel=Panel()
        panel.add_widget(WrappedLabel(text='OPTIONAL RELEASE UPDATES',bold=True,color=MUTED))
        panel.add_widget(WrappedLabel(text='Leave your email for release updates from the developer. Voluntary signups are counted; this is not a total download count.',color=MUTED))
        self.contact_editor=EditingField(multiline=False,hint_text='name@example.com',font_size=sp(16),
             size_hint_y=None,height=dp(48),background_normal='',background_color=CONTROL,foreground_color=TEXT)
        with self.model.store._connect() as db:
            row=db.execute("SELECT value FROM preferences WHERE key='release_contact_email'").fetchone()
        self.contact_editor.text=json.loads(row[0]) if row else ''
        panel.add_widget(self.contact_editor)
        self.contact_status=WrappedLabel(text='',color=MUTED)
        panel.add_widget(self.contact_status)
        self.contact_submit=LabButton(text='Save email',primary=True)
        self.contact_submit.bind(on_release=self.submit_contact)
        panel.add_widget(self.contact_submit)
        self.settings_content.add_widget(panel,index=len(self.settings_content.children))
        # A dismissible first-open invitation leaves the app fully usable.
        with self.model.store._connect() as db:
            seen=db.execute("SELECT value FROM preferences WHERE key='release_contact_seen'").fetchone()
        if not seen:
            from .app import ScreenPopup
            content=BoxLayout(orientation='vertical',spacing=dp(12),padding=dp(16))
            content.add_widget(WrappedLabel(text='Welcome to SMA Stock Analyzer. You can optionally receive release updates by email.'))
            signup=LabButton(text='Add email in Settings',primary=True)
            skip=LabButton(text='Skip for now')
            content.add_widget(signup);content.add_widget(skip)
            popup=ScreenPopup(self,title='Welcome',content=content,size_hint=(.9,None),height=dp(260))
            def done(*_):
                with self.model.store._connect() as db:
                    db.execute("INSERT OR REPLACE INTO preferences VALUES ('release_contact_seen','true')")
                popup.dismiss()
            skip.bind(on_release=done)
            signup.bind(on_release=lambda *_:(done(),self.show_settings()))
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
