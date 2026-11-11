"""Running UI motion/cancellation checks over controlled mobile HTTP fixtures."""
import json
import re
from dataclasses import replace
from pathlib import Path
from threading import Event
from unittest.mock import patch

from kivy.core.window import Window
from sma_analyzer.app import CustomValueField
from sma_analyzer.navigation import BottomSheet, SoftPageTransition
from scripts.smoke_ui_flow import FlowSmoke, temporary


class MotionSmoke(FlowSmoke):
    title="SMA motion and banner presentation · controlled test data"
    releases=()

    def capture(self,name,widget=None):
        root=Path("artifacts/ui-motion")
        root.mkdir(exist_ok=True,parents=True)
        (widget or self.screen).export_to_png(str(root/(name+".png")))

    def settled(self):
        yield lambda:not self.screen.manager.transition.is_active
        yield from self.frames(3)

    def steps(self):
        yield from super().steps()
        ui=self.screen
        ui.show_results()
        yield from self.settled()
        for width in (320,440):
            Window.size=(width,920)
            yield from self.frames()
            assert abs(ui.rename_button.right-ui.line_name_row.right)<1
            assert abs(ui.rename_button.center_y-ui.card_values["period"].center_y)<1
            assert ui.selected_target_badge.top<=ui.line_name_row.y+.5
            assert ui.named_period_caption.text==f"SMA ({ui.model.result.period} days)"
            assert not any(re.search(r"\b\d+ sessions\b",getattr(widget,"text","")) for widget in ui.walk())
        self.capture("chart-header")
        self.checked("pencil stays at the far right of the name at 320/440dp; target sits below and period labels use SMA (X days)")

        calls=len(self.client.calls)
        ui.backtest_period._dropdown.select("Custom")
        yield lambda:ui.backtest_custom_holder.progress==1
        assert isinstance(ui.backtest_years,CustomValueField) and isinstance(ui.custom_target,CustomValueField)
        assert ui.backtest_years.background_color==ui.custom_target.background_color
        assert ui.backtest_years.field_surface.radius==ui.custom_target.field_surface.radius
        assert not ui.backtest_years.disabled
        ui.backtest_years.text="1.5"
        ui.backtest_years.dispatch("on_text_validate")
        assert ui.backtest_report is not None and ui.backtest_custom_holder.height>44
        ui.scroll.scroll_to(ui.table_panel,animate=False)
        yield from self.frames()
        self.capture("custom-backtesting")
        assert len(self.client.calls)==calls
        self.checked("custom backtesting reveals the same rounded numeric field as target preferences and accepts fractional years locally")

        for scenario in ("dca","random"):
            ui.backtest_years.focus=True
            ui.show_backtest_help(scenario)
            sheet=ui.backtest_help_popup
            assert not ui.backtest_years.focus
            samples=[]
            sheet.bind(progress=lambda _,value:samples.append(value))
            assert isinstance(sheet,BottomSheet) and sheet.parent is ui
            yield lambda:sheet.progress==1
            assert any(0<value<1 for value in samples)
            assert abs(sheet.body.y-ui.y)<1 and sheet.body.top<=ui.top
            self.capture("help-"+scenario)
            assert ui.handle_back()
            yield lambda:sheet.parent is None
        self.checked("both help sheets share the saved drawer's upward animation, safe bounds and native Back dismissal")

        saved=ui.model.current_saved_line()
        ui.on_delete(saved)
        ui.open_unsaved_history()
        sheet=ui.history_popup
        samples=[]
        sheet.bind(progress=lambda _,value:samples.append(value))
        yield lambda:sheet.progress==1
        assert any(0<value<1 for value in samples)
        assert isinstance(sheet,BottomSheet)
        self.capture("recently-unsaved")
        archived=next(line for line in ui.model.store.recent_unsaved() if line.custom_name==saved.custom_name)
        ui.restore_unsaved(archived)
        yield lambda:sheet.parent is None
        yield from self.settled()
        assert ui.model.current_saved_line().custom_name==saved.custom_name
        assert sheet.parent is None
        self.checked("recently unsaved lines use the same bottom drawer and exact restoration dismisses it cleanly")

        ui.show_library()
        yield from self.settled()
        key=ui.model.dataset.counter
        if key in ui.expanded_saved_securities:
            ui.toggle_saved_security(key)
            yield lambda:ui.landing_security_groups[key]["reveal"].progress==0
        ui.library_scroll.scroll_to(ui.landing_security_groups[key]["group"],animate=False)
        yield from self.frames()
        samples=[]
        reveal=ui.landing_security_groups[key]["reveal"]
        reveal.bind(progress=lambda _,value:samples.append(value))
        self.tap(ui.landing_security_buttons[key])
        yield lambda:reveal.progress==1
        assert any(0<value<1 for value in samples)
        assert ui.saved_security_groups[key]["reveal"].progress==1
        self.capture("library-expanded")
        ui.toggle_saved_security(key)
        yield lambda:reveal.progress==0
        assert ui.landing_security_groups[key]["body"].parent is None
        ui.toggle_saved_security(key)
        ui.toggle_saved_security(key)
        ui.toggle_saved_security(key)
        yield lambda:reveal.progress==1
        assert not reveal.disabled
        self.checked("company accordions smoothly reveal/collapse on both menus and recover from rapid reversals without detached controls")

        for name in ("search","settings","results","crossovers","guide","library"):
            samples=[]
            def sample(_,progress):
                samples.append(progress)
            ui.manager.transition.bind(on_progress=sample)
            ui._navigate(name)
            yield from self.settled()
            ui.manager.transition.unbind(on_progress=sample)
            assert isinstance(ui.manager.transition,SoftPageTransition)
            assert any(0<value<1 for value in samples),(name,samples)
            assert ui.manager.current_screen.opacity==1
            assert ui.manager.current_screen.pos==ui.manager.pos
        ui.show_search();ui.show_settings();ui.go_back();ui.show_library()
        yield from self.settled()
        assert all(page.opacity==1 for page in ui.pages.values())
        self.checked("all six pages animate with intermediate frames and rapid forward/Back navigation restores positions and opacity")

        ui.show_parameters()
        yield from self.settled()
        ui.search_scroll.scroll_to(ui.target,animate=False)
        yield from self.frames()
        samples=[]
        ui.target._dropdown.bind(opacity=lambda _,value:samples.append(value))
        self.tap(ui.target)
        yield lambda:ui.target._dropdown.opacity==1
        assert ui.target.is_open and any(0<value<1 for value in samples)
        ui.target._dropdown.select(ui.target.text)
        ui.target.is_open=True  # Reopen before the selection fade-out completes.
        yield from self.frames(5)
        assert ui.target.is_open and ui.target._dropdown.parent is not None
        assert ui.handle_back()
        yield lambda:not ui.target.is_open
        assert ui.manager.current=="search" and ui.builder_selected
        self.checked("selector menus fade smoothly and native Back closes the menu before leaving preferences")
        ui.target.text="Custom"
        ui.custom_target.text="17"
        original=ui.model.result
        if original is None:
            original=ui.model.result_for_dataset(ui.model.dataset,saved.period,saved.target_frequency)
        releases=[Event(),Event()]
        starts=[Event(),Event()]
        cancelled=[Event(),Event()]
        self.releases=releases
        jobs=[]
        def delayed(prices,target,*,cancel,dates=None):
            index=len(jobs)
            jobs.append(target)
            starts[index].set()
            while not releases[index].wait(.01):
                if cancel.is_set():
                    cancelled[index].set()
            return replace(original,target_frequency=target)
        with patch("sma_analyzer.app.optimize_sma",side_effect=delayed):
            ui.on_optimize()
            yield lambda:starts[0].is_set()
            overlay=ui.optimization_overlay
            elapsed=overlay.logo.elapsed
            yield from self.frames(5)
            assert overlay.parent is ui and overlay.logo.elapsed>elapsed
            assert tuple(overlay.scrim.size)==tuple(ui.size) and overlay.card.center==ui.center
            assert not any(getattr(widget,"text","").lower()=="back" for widget in overlay.walk())
            self.capture("optimization-loading")
            assert ui.handle_back()
            yield lambda:cancelled[0].is_set()
            assert not ui.busy and overlay.parent is None
            assert ui.manager.current=="search" and ui.builder_selected
            assert ui.custom_target.text=="17"
            ui.custom_target.text="19"
            ui.on_optimize()
            assert ui.busy and overlay.parent is ui
            releases[0].set()
            yield lambda:starts[1].is_set()
            yield from self.frames(5)
            assert ui.busy and overlay.parent is ui and ui.model.result is None
            assert ui.handle_back()
            yield lambda:cancelled[1].is_set()
            releases[1].set()
            yield from self.frames(5)
            assert not ui.busy and overlay.parent is None and ui.model.result is None
        self.checked("logo paths animate above a dimmed modal background; native Back cancels in place and stale completion cannot dismiss a newer optimization")
        ui.on_optimize()
        yield lambda:not ui.busy
        yield from self.settled()
        assert ui.model.result.target_frequency==19 and ui.manager.current=="results"
        assert ui.optimization_overlay.parent is None
        with patch("sma_analyzer.app.optimize_sma",side_effect=AssertionError("cached analysis must be immediate")):
            ui.on_optimize()
            assert not ui.busy and ui.optimization_overlay.parent is None
        yield from self.settled()
        assert len(self.client.calls)==calls
        self.checked("optimization works after cancellation; completed/cached targets remove or avoid the overlay and require no data API call")

    def on_stop(self):
        for release in self.releases:
            release.set()
        self.screen.close()
        Path("artifacts/ui-motion-smoke.json").write_text(json.dumps({"passed":not self.failed,"checks":self.checks,
            "transport":"controlled mobile HTTP; Android OS presentation and sleeping phone not exercised"},indent=2))


if __name__=="__main__":
    app=MotionSmoke()
    app.run()
    temporary.cleanup()
    raise SystemExit(1 if app.failed else 0)
