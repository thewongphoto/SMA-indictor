"""An isolated lesson presented with the normal Charts UI, not a second chart."""
from pathlib import Path
from tempfile import TemporaryDirectory
from kivy.clock import Clock
from kivy.metrics import sp
from .guide import calculate_lesson, Lesson
from .model import AnalyzerModel
from .storage import LineStore
from .reference_market import GUIDE_SYMBOL, GUIDE_NAME


class GuidedExperience:
    def _build_guide(self):
        from .app import Panel, WrappedLabel, LabButton, MUTED
        self.guide_active=False
        self._guide_return=None
        self._guide_configuring=False
        self.guide_status=WrappedLabel(text='',color=MUTED)
        self.guide_content.add_widget(self.guide_status)
        cancel=LabButton(text='Finish example')
        cancel.bind(on_release=self.finish_guide)
        self.guide_content.add_widget(cancel)
        self.guide_intro=Panel()
        self.guide_intro.add_widget(WrappedLabel(text='Guided example',bold=True,font_size=sp(20)))
        self.guide_intro.add_widget(WrappedLabel(text='An SMA smooths closing prices. A crossing from below to above the line can suggest recovery, but prices can fall again.'))
        self.guide_intro.add_widget(WrappedLabel(text='Start with 4 signals a year, then compare equal-budget purchases in Backtest. This matches signal frequency, not profit.'))
        self.guide_finish_button=LabButton(text='Finish example')
        self.guide_finish_button.bind(on_release=self.finish_guide)
        self.guide_intro.add_widget(self.guide_finish_button)
        self.guide_gestures=WrappedLabel(text='Drag one finger to inspect closing and SMA values. Pinch with two fingers to zoom.',color=MUTED,font_size=sp(11))
        # Initial aliases are also used by keyboard/close lifecycle handlers.
        self.guide_chart=self.chart
        self.guide_backtest_years=self.custom_target

    def show_guide(self,*_):
        if self.guide_active:return
        self.finish_editing()
        if self.busy:self.cancel_optimization()
        self._guide_return=dict(model=self.model,target=self.target.text,custom=self.custom_target.text,
            horizon=self.backtest_period.text,years=self.backtest_years.text,
            timeline=self.chart.timeline,bounds=self.chart.viewport.bounds,scroll=self.scroll.scroll_y,
            stack=list(self._page_stack),origin=self._result_origin,selected=self.builder_selected,
            query=self.security_search.text,counter=self.counter.security)
        self.guide_active=True
        self._navigate('guide')
        self.guide_busy=True
        self._guide_job+=1
        token=self._guide_job
        self.guide_status.text='Loading the historical example…'
        provider=self.model.data_provider
        def load():
            data=None
            if self.yahoo_enabled:
                security=next((x for x in provider.search(GUIDE_SYMBOL) if x.ticker==GUIDE_SYMBOL),None)
                if security is None:raise ValueError('The VOO example is currently unavailable.')
                data=provider.historical_data(security)
            return calculate_lesson(4,data)
        future=self.market_executor.submit(load)
        future.add_done_callback(lambda done:Clock.schedule_once(lambda _:self._guide_complete(done,token),0))

    def _guide_complete(self,future,token):
        if self.closed or token!=self._guide_job or not self.guide_active:return
        self.guide_busy=False
        try:
            lesson=future.result()
            self._guide_temp=TemporaryDirectory(prefix='sma-guide-',dir=self.model.store.path.parent)
            self.model=AnalyzerModel(LineStore(Path(self._guide_temp.name)/'lesson.sqlite3'),
                                     data_provider=self._guide_return['model'].data_provider)
            self.model.apply_dataset(lesson.dataset)
            self.model.target_frequency=4
            self.model.apply_result(lesson.result)
            self._syncing_controls=True
            try:
                self.target.text='4 / year'
                self.counter.set_security(self.model.security(lesson.dataset.counter))
            finally:self._syncing_controls=False
            self.backtest_period.text='Max'
            self.content.add_widget(self.guide_intro,index=len(self.content.children))
            self.plot_panel.add_widget(self.guide_gestures)
            self.refresh()
            self.chart.set_timeline('1Y')
            self.show_results()
            self.scroll.scroll_y=1
        except Exception as error:
            self.guide_status.text=f'Could not load the example: {error}. Finish and try again.'

    def refresh_guide(self):
        if not getattr(self,'guide_active',False) or self.model is self._guide_return['model']:return
        self.guide_chart=self.chart
        self.guide_target=self.target
        self.guide_backtest_period=self.backtest_period
        self.guide_backtest_years=self.backtest_years
        self.guide_backtest_heading=self.backtest_heading
        self.guide_backtest_custom_holder=self.backtest_custom_holder
        self.guide_scroll=self.scroll
        self.guide_content=self.content
        self.guide_identity=self.plot_title
        self.guide_values=self.backtest_details
        self.guide_price_note=self.plot_subtitle
        self.guide_lesson=Lesson(self.model.dataset,self.model.result,self.backtest_report)
        self.guide_status.text=f'{GUIDE_NAME} ({GUIDE_SYMBOL})' if self.yahoo_enabled else 'Educational example'
        self.save_button.disabled=True
        self.save_button.opacity=0
        self.saved_menu_label.disabled=True

    def finish_guide(self,*_,navigate=True):
        if not self.guide_active:return
        self._guide_job+=1
        self._job+=1
        self._cancel_optimization.set()
        self.busy=self.guide_busy=False
        saved=self._guide_return
        self.guide_active=False
        self.model=saved['model']
        self._page_stack=saved['stack']
        self._result_origin=saved['origin']
        if self.guide_intro.parent:self.guide_intro.parent.remove_widget(self.guide_intro)
        if self.guide_gestures.parent:self.guide_gestures.parent.remove_widget(self.guide_gestures)
        self._syncing_controls=True
        try:
            self.target.text=saved['target']
            self.custom_target.text=saved['custom']
            self.counter.set_security(saved['counter'])
            self.backtest_years.text=saved['years']
            self.backtest_period.text=saved['horizon']
        finally:self._syncing_controls=False
        self.security_search.text=saved['query']
        self._builder_stage(saved['selected'])
        self.saved_menu_label.disabled=False
        self.save_button.opacity=1
        self.refresh()
        self.chart.set_timeline(saved['timeline'])
        self.chart.viewport.start,self.chart.viewport.end=saved['bounds']
        self.chart.redraw()
        self.scroll.scroll_y=saved['scroll']
        if hasattr(self,'_guide_temp'):self._guide_temp.cleanup();del self._guide_temp
        self._guide_return=None
        if navigate:self.show_library()
