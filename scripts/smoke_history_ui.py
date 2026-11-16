"""Frozen training history, stale results and explicit save choices in Kivy."""
from pathlib import Path
from kivy.core.window import Window
from scripts.smoke_ui_flow import FlowSmoke,temporary

class HistorySmoke(FlowSmoke):
    def steps(self):
        yield from super().steps()
        ui=self.screen;model=ui.model
        out=Path('artifacts/history-ui');out.mkdir(parents=True,exist_ok=True)
        old=model.current_saved_line();assert old
        model.store.set_notifications(old.id,'phone',False)
        model.store.set_line_alert(old.id,'monitor_start',False)
        model.store.rename(old.id,'My preserved line');model.store.set_color(old.id,2)
        ui.refresh();old=model.current_saved_line();color=model.store.line_color_index(old)
        assert ui.price_history_button.parent is ui.preference_body
        ui.show_history_picker();yield lambda:ui.price_history_sheet.progress==1
        ui.history_presets[3].dispatch('on_release')
        ui.price_history_sheet.dismiss();yield lambda:ui.price_history_sheet.parent is None
        assert model.history_start=='' and not model.history_stale
        ui.show_history_picker();yield lambda:ui.price_history_sheet.progress==1
        dates=model.dataset.dates;original=model.result;calls=len(self.client.calls)
        ui.history_presets['Custom dates'].dispatch('on_release')
        ui.history_from.text=dates[-2];ui.history_to.text=dates[-1]
        yield from self.frames()
        assert ui.history_apply.disabled and '4 trading days' in ui.history_readout.text
        ui.history_from.text=dates[80];ui.history_to.text=dates[-80]
        yield from self.frames()
        assert not ui.history_apply.disabled
        ui.price_history_sheet.export_to_png(str(out/'picker.png'))
        ui.history_apply.dispatch('on_release');yield lambda:ui.price_history_sheet.parent is None
        assert model.history_stale and model.result is original
        assert ui.save_button.disabled and 'Recalculate' in ui.detail_optimize_button.text
        assert len(self.client.calls)==calls
        ui.show_results();yield from self.frames()
        ui.export_to_png(str(out/'stale.png'))
        ui.on_detail_optimize();yield lambda:not ui.busy
        assert model.result.history_start==dates[80] and not model.history_stale
        assert model.result.history_end==dates[-80]
        ui.on_save();yield lambda:ui.history_save_sheet.progress==1
        ui.history_save_sheet.export_to_png(str(out/'save-choice.png'))
        ui.history_save_buttons['Update this line'].dispatch('on_release');yield lambda:ui.history_save_sheet.parent is None
        updated=model.store.get_line(old.id)
        assert updated.custom_name=='My preserved line' and not updated.push_enabled and not updated.alert_start
        assert model.store.line_color_index(updated)==color and updated.history_start==dates[80]
        ui.show_history_picker();yield lambda:ui.price_history_sheet.progress==1
        ui.history_presets[None].dispatch('on_release');ui.history_apply.dispatch('on_release');yield lambda:ui.price_history_sheet.parent is None
        ui.on_detail_optimize();yield lambda:not ui.busy
        ui.on_save();yield lambda:ui.history_save_sheet.progress==1
        ui.history_save_buttons['Save as a new line'].dispatch('on_release');yield lambda:ui.history_save_sheet.parent is None
        fresh=model.current_saved_line();assert fresh and fresh.id!=old.id
        assert fresh.push_enabled and fresh.alert_buy and fresh.alert_monitor and fresh.alert_start
        assert model.store.get_line(old.id)==updated
        assert len(self.client.calls)==calls
        ui.show_library();ui.expanded_saved_securities.add(model.dataset.counter);ui._refresh_saved();yield from self.frames()
        ui.export_to_png(str(out/'home.png'))
        ui.show_settings();ui.show_results();yield from self.frames()
        self.checked('history is available before calculation; real limits block short dates, selection makes results stale without requests, explicit recalc preserves full prices, Update keeps identity/name/colour/alerts, New keeps both with alerts on')

if __name__=='__main__':
    app=HistorySmoke();app.run();temporary.cleanup();raise SystemExit(1 if app.failed else 0)
