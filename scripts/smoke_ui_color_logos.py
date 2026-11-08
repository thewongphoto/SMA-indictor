"""Colour persistence, VOO lesson, offline logos and sustained mobile-worker motion."""
import json
import time
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from kivy.core.window import Window
from kivy.graphics import Ellipse
from kivy.metrics import dp
from sma_analyzer.engine import optimize_sma
from sma_analyzer.palette import COLOR_CHOICES,line_color
from scripts.smoke_ui_motion import MotionSmoke,temporary
from scripts.yahoo_test_data import bars_ending
from scripts.spinner_metrics import observe_spinner


class ColorLogoSmoke(MotionSmoke):
    frame_event=None
    performance={}

    def capture(self,name,widget=None):
        root=Path("artifacts/ui-0.11.0")
        root.mkdir(exist_ok=True,parents=True)
        (widget or self.screen).export_to_png(str(root/(name+".png")))

    def steps(self):
        yield from super().steps()
        ui=self.screen
        assert self.client.calls[0]==("history","VOO",{"period":"5d"})
        original_data,original_result=ui.model.dataset,ui.model.result
        ui.show_guide()
        yield lambda:not ui.guide_busy
        yield from self.settled()
        assert ui.guide_lesson.dataset.counter=="YAHOO:VOO"
        assert "Vanguard S&P 500 ETF (VOO)" in ui.guide_status.text
        assert ui.guide_identity.security.ticker=="VOO" and not ui.guide_identity.logo.is_fallback
        assert ui.model.dataset is original_data and ui.model.result is original_result
        self.capture("voo-guide")
        self.checked("startup probes VOO; the guide always uses named Vanguard S&P 500 ETF data without changing the selected company/chart")

        ui.show_results()
        yield from self.settled()
        ui.on_save()
        ui.saved_sheet.dismiss(animate=False)
        yield from self.frames()
        saved=ui.model.current_saved_line()
        calls=len(self.client.calls)
        before_result=ui.model.result
        for width in (320,440):
            Window.size=(width,920)
            ui.scroll.scroll_y=1
            yield from self.frames()
            assert ui.color_button.right<=ui.rename_button.x+1
            assert abs(ui.color_button.center_y-ui.rename_button.center_y)<1
            self.tap(ui.color_button)
            yield lambda:ui.color_popup.progress==1
            assert len(ui.color_buttons)==12
            assert len({tuple(button.swatch) for button in ui.color_buttons.values()})==12
            assert all(button.width>=44 and button.height>=44 for button in ui.color_buttons.values())
            for button in ui.color_buttons.values():
                swatch=next(item for item in button.canvas.before.children if isinstance(item,Ellipse))
                assert abs(swatch.pos[0]+swatch.size[0]/2-button.x-button.width/2)<.5
                assert swatch.pos[0]-dp(5)>=button.x and swatch.pos[0]+swatch.size[0]+dp(5)<=button.right
                assert button.halign=="center" and abs(button.text_size[0]-button.width)<.5
            self.capture("colour-picker-"+str(width))
            ui.handle_back()
            yield lambda:ui.color_popup.parent is None
        self.tap(ui.color_button)
        yield lambda:ui.color_popup.progress==1
        self.tap(ui.color_buttons[10])
        yield lambda:ui.color_popup.parent is None
        assert tuple(ui.card_values["period"].color)==COLOR_CHOICES[10]
        assert tuple(ui.saved_rows[saved.id]["swatch"].ink)==COLOR_CHOICES[10]
        assert tuple(ui.landing_saved_rows[saved.id]["swatch"].ink)==COLOR_CHOICES[10]
        assert line_color(ui.model.plot_lines()[-1].color_index)==COLOR_CHOICES[10]
        assert ui.model.result is before_result and len(self.client.calls)==calls
        self.capture("chosen-sma-colour")
        self.checked("palette icon sits left of pencil; 12 tappable colours fit 320/440dp and update chart, title and both menus without fetching or optimizing")

        ui.on_delete(saved)
        ui.open_unsaved_history()
        yield lambda:ui.history_popup.progress==1
        archived=next(line for line in ui.model.store.recent_unsaved() if line.period==saved.period)
        ui.restore_unsaved(archived)
        yield lambda:ui.history_popup.parent is None
        assert line_color(ui.model.store.color_index(saved.counter,saved.scenario,saved.period))==COLOR_CHOICES[10]
        self.checked("selected colour survives the actual unsave/restore UI")

        ui.show_search()
        yield from self.settled()
        ui.security_search.text="dbs"
        ui.submit_security_search()
        yield lambda:not ui.search_busy
        assert not ui.security_match_buttons[0].logo_is_fallback
        security=ui.search_results[0]
        # Simulate a previously cached record from before logo/type metadata.
        old=replace(security,logo="",instrument_type="",issuer="")
        ui.model.data_provider.cache.put_security(old)
        ui.submit_security_search()
        yield lambda:not ui.search_busy
        assert ui.search_results[0].logo=="" and ui.search_results[0].instrument_type==""
        ui.select_security_match(ui.search_results[0])
        yield lambda:not ui.history_loading
        yield from self.frames()
        assert not ui.counter.logo.is_fallback and not ui.plot_title.logo.is_fallback
        assert ui.counter.security.logo_path.endswith("dbs.png")
        self.capture("dbs-company-logo")
        self.checked("DBS search, selected-security and chart identities use the company logo even with legacy cached metadata")

        for ticker,stem in (("VOO","vanguard"),("SPY","state-street")):
            ui.show_search()
            yield from self.settled()
            ui.security_search.text=ticker
            ui.submit_security_search()
            yield lambda:not ui.search_busy
            assert not ui.security_match_buttons[0].logo_is_fallback
            ui.select_security_match(ui.search_results[0])
            yield lambda:not ui.history_loading
            yield from self.frames()
            assert ui.counter.security.logo_path.endswith(stem+".png")
            assert not ui.counter.logo.is_fallback
            self.capture(ticker.lower()+"-issuer-logo")
        self.checked("VOO and SPY consistently display Vanguard and State Street issuer logos through the mobile search/history path")

        # Exercise sustained motion while the actual non-NumPy mobile scorer
        # competes with the UI, rather than only sleeping in a mocked worker.
        old_data=ui.model.dataset
        bars=bars_ending(count=6800)
        data=replace(old_data,prices=tuple(bar["adj_close"] for bar in bars),
                     dates=tuple(bar["date"] for bar in bars),revision=old_data.revision+1)
        ui.model.apply_dataset(data)
        ui.show_parameters()
        yield from self.settled()
        ui.target.text="Custom";ui.custom_target.text="23"
        ui.refresh()
        samples=[]
        def record(_,angle):
            samples.append((time.perf_counter(),angle))
        spinner=ui.optimization_overlay.spinner
        spinner.bind(angle=record)
        with patch("sma_analyzer.app.optimize_sma",side_effect=lambda *args,**kwargs:optimize_sma(*args,use_fast=False,**kwargs)):
            ui.on_optimize()
            started=time.perf_counter()
            while time.perf_counter()-started<3.3:
                assert ui.busy,"The mobile-sized workload should still be running during the motion sample"
                yield lambda:True
            # Hosted software rendering may be slower than a developer laptop.
            # Verify sustained motion, no pauses and clock-correct rotation;
            # a fixed frame count incorrectly rejected a healthy 55-frame run.
            self.performance,problems=observe_spinner(samples,started,time.perf_counter())
            assert not problems,{"problems":problems,**self.performance}
            assert spinner._spin_event is not None
            self.capture("continuous-spinner")
            assert ui.handle_back()
            assert not ui.busy and spinner._spin_event is None
        spinner.unbind(angle=record)
        ui.model.apply_dataset(old_data)
        ui.refresh()
        self.checked("GPU-rotated spinner continues beyond three revolutions during real 6800-day mobile scoring, then cancels cleanly")

    def on_stop(self):
        for release in self.releases:
            release.set()
        self.screen.close()
        Path("artifacts/ui-color-logos-smoke.json").write_text(json.dumps({"passed":not self.failed,
            "checks":self.checks,"performance":self.performance,
            "transport":"controlled mobile HTTP; desktop CPU timing, not measured Android FPS"},indent=2))


if __name__=="__main__":
    app=ColorLogoSmoke()
    app.run()
    temporary.cleanup()
    raise SystemExit(1 if app.failed else 0)
