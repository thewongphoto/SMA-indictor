"""Real Kivy gesture/layout checks over controlled mobile HTTP responses.

No live provider calls and no user cache. Screenshots are test data, not market
observations. Pinches use the actual window/ScrollView/grab coordinate pipeline.
"""
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

from scripts.smoke_mobile_yahoo_ui import MobileYahooSmoke,temporary
from scripts.smoke_ui import Pointer
from sma_analyzer.app import AnalyzerScreen
from sma_analyzer.model import AnalyzerModel
from sma_analyzer.storage import LineStore
from sma_analyzer.palette import line_color


class RefinementSmoke(MobileYahooSmoke):
    title = "UI refinements · controlled HTTP test data"

    def frames(self,count=8):
        for _ in range(count):
            yield lambda:True

    def capture(self,name,widget=None):
        root=Path("artifacts/ui-0.9")
        root.mkdir(parents=True,exist_ok=True)
        (widget or self.screen).export_to_png(str(root/(name+".png")))

    def steps(self):
        ui=self.screen
        yield lambda:not ui._source_check_busy
        for width,height in ((320,640),(440,920)):
            Window.size=(width,height)
            for page in ui.pages:
                ui._navigate(page)
                yield from self.frames(3)
                gear=ui.page_settings_buttons[page]
                assert gear.kind=="settings" and gear.center_x>ui.center_x
                assert gear.right<=ui.right and gear.height>=dp(44)
        self.checked("settings stays at the top right on all seven screens at phone widths")
        ui.show_library()
        ui.show_guide()
        yield lambda:not ui.guide_busy
        assert not ui.guide_lesson.dataset.is_simulated
        assert ui.guide_lesson.dataset.counter=="YAHOO:SPY"
        assert ui.model.dataset.counter=="UNSELECTED"
        assert ui.guide_chart.viewport.dates==ui.guide_lesson.dataset.dates
        assert ui.guide_chart.prices==tuple(b["adj_close"] for b in self.client.bars)
        assert ui.guide_chart.price_label=="Adj. close"
        self.checked("live guided lesson downloads actual provider data without changing selection")
        ui.show_search()
        ui.security_search.text="apple"
        ui.submit_security_search()
        yield lambda:not ui.search_busy
        ui.select_security_match(ui.search_results[0])
        yield lambda:not ui.history_loading
        assert ui.custom_toggle.parent is None
        ui.on_optimize()
        yield lambda:not ui.busy
        result=ui.model.result
        calls=len(self.client.calls)
        ui.show_parameters()
        with patch.object(ui.executor,"submit",side_effect=AssertionError("must reuse cached analysis")):
            ui.on_optimize()
        assert ui.manager.current=="results" and ui.model.result==result and not ui.busy
        assert len(self.client.calls)==calls
        self.checked("Optimize instantly reuses an unsaved cached target with no fetch/optimizer")
        data=ui.model.dataset
        ui.model.store.save(data.counter,data.scenario,9,6)
        ui.model.store.save(data.counter,data.scenario,29,12)
        ui.show_parameters()
        ui.target.text="6 / year"
        with patch.object(ui.executor,"submit",side_effect=AssertionError("must reuse saved period")):
            ui.on_optimize()
        assert ui.model.result.period==9 and ui.model.viewing_saved
        assert len(self.client.calls)==calls
        self.checked("Optimize opens matching saved target's exact period without a calculation")
        ui.expanded_saved_securities.add(data.counter)
        ui.refresh()
        for saved in ui.model.saved_lines():
            ui.on_view_saved(saved)
            yield lambda:not ui.history_loading
            actual={line.period:ui.chart.line_color(line,i) for i,line in enumerate(ui.chart.series)}
            assert actual=={9:line_color(0),29:line_color(1)}
            assert ui.saved_rows[saved.id]["swatch"].ink==actual[saved.period]
        self.checked("both saved SMA colors and swatches stay fixed when selection changes")
        ui.saved_sheet.dismiss(animate=False)
        ui.chart.set_timeline("Max")
        yield from self.frames()
        self.capture("results")
        self.capture("search-plus",ui.new_security_button)
        assert not hasattr(ui,"saved_menu_button")
        ui.new_security_button.dispatch("on_release")
        assert ui.manager.current=="search"
        ui.show_results()
        self.checked("the theme-native search-plus opens Choose a security; Saved SMAs has no hamburger")
        ui.backtest_period._dropdown.select("3Y")
        report=ui.backtest_report
        assert f"USD {report.crossings.invested:,.0f}" in ui.backtest_contribution.text
        assert f"{len(report.crossings.indices)} upward crossings" in ui.backtest_contribution.text
        assert ui.backtest_gain.text==f"{report.crossings.return_percent:+.2f}%"
        assert all("vs a" in label.text for label in ui.backtest_differences.values())
        yield from self.frames()
        self.capture("backtesting",ui.table_panel)
        loss=replace(report,crossings=replace(report.crossings,ending_value=report.crossings.invested*.9))
        with patch("sma_analyzer.app.compare_investments",return_value=loss):
            ui._refresh_backtest()
        assert ui.backtest_gain_icon.kind=="loss" and ui.backtest_gain.text=="-10.00%"
        original=ui.model.result
        ui.model.result=replace(original,events=())
        ui._refresh_backtest()
        assert ui.backtest_gain.text=="N/A" and ui.backtest_gain_icon.opacity==0
        ui.model.result=original
        ui._refresh_backtest()
        self.checked("backtesting shows contributed amount, A growth, and separate B/C comparisons")
        for page in ui.pages:
            texts=[w.text.lower() for w in ui.pages[page].walk() if isinstance(w,(Label,TextInput))]
            assert not any("yahoo" in text or "simulat" in text for text in texts),page
        self.checked("all live screen text is free of provider branding and simulation labels")
        ui.show_results()
        ui.chart.set_timeline("1Y")
        ui.scroll.scroll_to(ui.chart,animate=False)
        yield from self.frames(10)
        chart=ui.chart
        initial=chart.viewport.bounds
        def location(fraction):
            left,bottom,width,height=chart.plot_rect
            return chart.to_window(left+fraction*width,bottom+.5*height)
        one,two=Pointer(*location(.35)),Pointer(*location(.65))
        one.down();two.down()
        # Only one pointer's MotionEvent is chart-local during grabbed dispatch.
        # Alternate the moving finger and allow Kivy to restore the other's coords.
        spans=[]
        for fraction in (.34,.33,.32,.31,.30):
            one.move_to(*location(fraction))
            yield from self.frames(2)
            spans.append(chart.viewport.end-chart.viewport.start)
        assert all(a>b for a,b in zip(spans,spans[1:])),spans
        assert max(a-b for a,b in zip(spans,spans[1:]))<.12*(initial[1]-initial[0])
        assert any(x!=round(x) for x in chart.viewport.bounds)
        two.move_to(*location(.75))
        yield from self.frames(5)
        one.up()
        bounds=chart.viewport.bounds
        two.move_to(*location(.80));two.up()
        assert chart.viewport.bounds==bounds and chart.inspection is None
        for left,right in zip(chart.axis_ticks,chart.axis_ticks[1:]):
            assert right.center-right.width/2>=left.center+left.width/2+dp(10)
        self.checked("pinch has continuous fractional ranges, stable mixed coordinates and no lift jump")
        self.capture("pinch",chart.parent)
        for i in range(130):
            self.cache.operation("history","AAPL","cache_hit",f"Test event {i}")
        ui.show_api_log()
        yield from self.frames(10)
        assert ui.api_log_entries.height>ui.api_log_scroll.height
        calls=len(self.client.calls)
        scroll=ui.api_log_scroll
        touch=Pointer(*scroll.to_window(*scroll.center))
        touch.down()
        for delta in (20,40,60,80,100):
            touch.move_to(*scroll.to_window(scroll.center_x,scroll.center_y+delta))
            yield from self.frames(1)
        touch.up()
        yield from self.frames(5)
        assert scroll.scroll_y<.99,scroll.scroll_y
        older=next(w for w in ui.api_log_popup.content.children if getattr(w,"text","")=="Load older calls")
        older.dispatch("on_release")
        yield from self.frames(8)
        assert "Test event 0" in ui.api_log_report
        assert len(self.client.calls)==calls
        assert "yahoo" not in ui.api_log_report.lower()
        self.capture("request-log",ui.api_log_popup)
        assert ui.handle_back()
        self.checked("request log scrolls with real touch and loads older calls without network")
        ui.show_search()
        ui.security_search.text="DBS"
        ui.submit_security_search()
        yield lambda:not ui.search_busy
        ui.select_security_match(ui.search_results[0])
        yield lambda:not ui.history_loading
        sg=ui.model.dataset
        ui.model.store.save(sg.counter,sg.scenario,9,6)
        ui.on_view_saved(ui.model.saved_lines()[0])
        assert ui.model.dataset.currency=="SGD" and "SGD adjusted daily close" in ui.plot_subtitle.text
        assert ui.backtest_values["crossings"].text.startswith("USD ")
        assert "currency movements are excluded" in ui.backtest_details.text
        assert ui.model.store.color_index(sg.counter,sg.scenario,9)==0
        self.checked("SG prices keep SGD on chart; USD price-return comparisons explicitly exclude FX")
        # A cold screen reconstructs saved groups, but never their expansion state.
        fresh=AnalyzerScreen(AnalyzerModel(LineStore(ui.model.store.path),self.provider))
        ui.close()
        Window.remove_widget(ui)
        Window.add_widget(fresh)
        self.root=self.screen=fresh
        yield from self.frames(10)
        assert fresh.manager.current=="library" and fresh.library_state=="populated"
        assert fresh.expanded_saved_securities==set()
        assert len(fresh.landing_security_groups)==2
        for groups in (fresh.saved_security_groups,fresh.landing_security_groups):
            assert all(group["body"].parent is None for group in groups.values())
        self.capture("library-collapsed")
        self.checked("cold launch collapses every saved security in both library and chart menus")

    def on_stop(self):
        self.screen.close()
        Path("artifacts/ui-refinements-smoke.json").write_text(json.dumps(
            {"passed":not self.failed,"checks":self.checks,
             "transport":"controlled HTTP fixtures; no physical-phone smoothness claim"},indent=2))


if __name__=="__main__":
    app=RefinementSmoke()
    app.run()
    temporary.cleanup()
    raise SystemExit(1 if app.failed else 0)
