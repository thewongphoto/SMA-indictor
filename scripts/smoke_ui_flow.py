"""Merged builder and saved-name gestures over controlled mobile HTTP fixtures."""
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from kivy.core.window import Window
from kivy.uix.label import Label
from scripts.smoke_mobile_yahoo_ui import MobileYahooSmoke,temporary
from scripts.smoke_ui import Pointer


class FlowSmoke(MobileYahooSmoke):
    title="Merged builder and named SMAs · test data"

    def frames(self,count=8):
        for _ in range(count): yield lambda:True

    def capture(self,name,widget=None):
        root=Path("artifacts/ui-0.10")
        root.mkdir(exist_ok=True,parents=True)
        (widget or self.screen).export_to_png(str(root/(name+".png")))

    def tap(self,widget):
        pointer=Pointer(*widget.to_window(*widget.center))
        pointer.down();pointer.up()

    def steps(self):
        ui=self.screen
        Window.size=(440,920)
        yield lambda:not ui._source_check_busy
        ui.new_analysis_button.dispatch("on_release")
        yield from self.frames()
        builder=ui.manager.current_screen
        assert builder is ui.pages["search"] and len(ui.pages)==6
        assert "parameters" not in ui.pages and not hasattr(ui,"refresh_search_button")
        assert ui.controls.parent is None and ui.page_titles["search"].text=="Choose a security"
        self.capture("choose-security")
        self.checked("one builder screen; empty stage hides preferences and has no Refresh search button")
        ui.security_search.text="apple"
        calls=len(self.client.calls)
        yield from self.frames(2)
        assert len(self.client.calls)==calls
        self.tap(ui.search_submit)
        yield lambda:not ui.search_busy
        yield from self.frames(4)
        samples=[]
        ui.preference_reveal.bind(progress=lambda _,value:samples.append(value))
        self.tap(ui.security_match_buttons[0])
        yield lambda:not ui.history_loading
        yield lambda:ui.preference_reveal.progress==1
        yield from self.frames(4)
        assert ui.manager.current_screen is builder
        assert any(0<value<1 for value in samples),samples
        assert all(a<=b for a,b in zip(samples,samples[1:])),samples
        assert ui.page_titles["search"].text=="Set your preference"
        assert ui.counter.security.name=="Apple Inc." and ui.optimize_button.get_parent_window() is not None
        self.capture("set-preference")
        self.checked("real selection stays on the same screen and reveals target/Optimize with intermediate animation frames")
        ui.search_scroll.scroll_to(ui.optimize_button,animate=False)
        yield from self.frames()
        self.tap(ui.optimize_button)
        yield lambda:not ui.busy
        assert ui.manager.current=="results" and ui.model.result is not None
        result=ui.model.result
        yield from self.frames()
        self.tap(ui.save_button)
        assert ui.model.current_saved_line() is not None
        ui.saved_sheet.dismiss(animate=False)
        yield from self.frames()
        assert ui.rename_button.parent is ui.line_name_row
        self.tap(ui.rename_button)
        yield from self.frames()
        assert ui.rename_popup._is_open
        ui.rename_editor.text="Recovery plan"
        self.capture("rename-line",ui.rename_popup)
        self.tap(ui.rename_save_button)
        yield from self.frames()
        saved=ui.model.current_saved_line()
        assert saved.custom_name=="Recovery plan" and ui.model.result is result
        assert ui.card_values["period"].text=="Recovery plan"
        assert str(result.target_frequency) in ui.selected_target_badge.text
        assert f"{result.period} sessions" in ui.named_period_caption.text
        assert "Recovery plan" in ui.legend_labels and ui.chart.inspection_name=="Recovery plan"
        assert "Recovery plan" in ui.saved_rows[saved.id]["title"].text
        assert "Recovery plan" in ui.landing_saved_rows[saved.id]["title"].text
        assert "Recovery plan" in ui.backtest_section_title.text
        assert ui.backtest_details.text==""
        self.capture("named-chart")
        self.capture("backtesting",ui.table_panel)
        ui.show_more_crossings()
        assert any("Recovery plan" in w.text for w in ui.full_table_panel.walk() if isinstance(w,Label))
        ui.go_back()
        self.checked("renaming propagates to card, target badge, chart, inspector, both menus, backtest and crossing details without retuning")
        # Full names remain editable; legend bounds constrain long names on phones.
        Window.size=(320,640)
        yield from self.frames()
        ui.show_rename_line()
        yield from self.frames(4)
        ui.rename_editor.text="A long named recovery strategy with a carefully chosen SMA"
        self.tap(ui.rename_save_button)
        yield from self.frames()
        assert all(item.width<=ui.legend.parent.width+.1 for item in ui.legend.children)
        ui.show_rename_line()
        yield from self.frames(4)
        ui.rename_editor.text="x"*61
        ui.rename_save_button.dispatch("on_release")
        assert ui.rename_popup._is_open and "60" in ui.rename_status.text
        ui.size_hint=(None,None)
        ui.pos=(0,220)
        ui.size=(320,420)
        yield from self.frames(3)
        assert ui.rename_popup.y>=ui.y and ui.rename_popup.top<=ui.top
        ui.rename_editor.text="Recovery plan"
        ui.rename_save_button.dispatch("on_release")
        ui.pos=(0,0);ui.size=Window.size;ui.size_hint=(1,1)
        Window.size=(440,920)
        yield from self.frames()
        self.checked("name validation, long legend bounds and keyboard-safe dialog position on a small phone")
        saved=ui.model.current_saved_line()
        ui.on_delete(saved)
        ui.open_unsaved_history()
        yield from self.frames()
        archived=next(line for line in ui.model.store.recent_unsaved() if line.period==result.period)
        assert archived.custom_name=="Recovery plan"
        assert any("Recovery plan" in w.text for w in ui.history_popup.content.walk() if isinstance(w,Label))
        self.capture("archive",ui.history_popup)
        ui.restore_unsaved(archived)
        assert ui.model.current_saved_line().custom_name=="Recovery plan"
        ui.change_parameters_button.dispatch("on_release")
        yield from self.frames()
        assert ui.manager.current_screen is builder and ui.builder_selected
        assert ui.counter.security.name=="Apple Inc." and ui.preference_reveal.progress==1
        assert ui.page_titles["search"].text=="Set your preference"
        self.checked("archive/restore retains the name and Change parameters returns to the selected stage of the same builder")
        ui.show_library()
        ui.expanded_saved_securities.add(ui.model.dataset.counter)
        ui._refresh_saved()
        yield from self.frames()
        self.capture("named-library")
        ui.show_settings()
        ui.settings_scroll.scroll_to(ui.settings_panel,animate=False)
        yield from self.frames()
        assert any("6:30am" in w.text and "6:30pm" in w.text for w in ui.settings_panel.walk() if isinstance(w,Label))
        self.capture("notification-settings")
        self.checked("settings explains Singapore-time market schedules and desktop/native delivery scope")
        calls=len(self.client.calls)
        data=ui.model.dataset
        ui.model.active_visible=False
        ui.refresh()
        bars,fetched,_=self.cache.history(data.counter)
        bars[-1]=dict(bars[-1],close=bars[-1]["close"]+.5,adj_close=bars[-1]["adj_close"]+.5)
        self.cache.merge_history(ui.model.security(data.counter),bars,fetched)
        period=ui.model.result.period
        ui.resume_cached_prices()
        assert ui.model.dataset.prices[-1]==bars[-1]["adj_close"]
        assert ui.model.result.period==period and ui.model.current_saved_line().custom_name=="Recovery plan"
        assert not ui.model.active_visible
        assert len(self.client.calls)==calls
        self.checked("returning from background applies locally refreshed prices while preserving saved name/period and making no API call")
        saved=ui.model.current_saved_line()
        ui.model.store.set_notifications(saved.id,"phone",True)
        ui.model.store.save_notification_settings(replace(ui.model.store.notification_settings(),phone_buy=True))
        calls=len(self.client.calls)
        with patch("sma_analyzer.app.platform","android"), \
             patch("sma_analyzer.native_schedule.sync_schedules",return_value="Scheduled test"), \
             patch("sma_analyzer.app.AndroidNotifier.request_permission") as permission:
            ui.sync_notification_schedule()
            ui.sync_notification_schedule()
            assert permission.call_count==1
            permission.call_args.args[0](False)
            yield from self.frames(2)
            assert permission.call_count==1
            assert self.cache.preference("android_notification_permission_asked_v1")
        assert len(self.client.calls)==calls
        self.checked("existing enabled alerts request Android permission once; denial does not create a repeat prompt or API call")

    def on_stop(self):
        self.screen.close()
        Path("artifacts/ui-flow-smoke.json").write_text(json.dumps({"passed":not self.failed,"checks":self.checks,
            "transport":"controlled mobile HTTP responses; native sleep/notification delivery not exercised"},indent=2))


if __name__=="__main__":
    app=FlowSmoke()
    app.run()
    temporary.cleanup()
    raise SystemExit(1 if app.failed else 0)
