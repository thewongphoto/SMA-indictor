"""Four-tab navigation, appearance, line editing and narrow layouts."""
from pathlib import Path
from kivy.core.window import Window
from kivy.metrics import dp
from scripts.smoke_ui_flow import FlowSmoke, temporary
from sma_analyzer.appearance import mapped
from sma_analyzer.theme import TEXT, BG
from kivy.graphics import Rectangle


class RedesignSmoke(FlowSmoke):
    def steps(self):
        yield from super().steps()
        ui=self.screen
        out=Path('artifacts/redesign-ui');out.mkdir(parents=True,exist_ok=True)
        # Move the root like Android inset/IME updates. The cached Kivy top alias
        # used to leave the canvas divider at the previous root's y position.
        ui.size_hint=(None,None)
        Window.size=(390,844)
        for destination in ('library','results','alerts','settings'):
            ui.select_tab(destination)
            yield from self.frames(12)
            for bottom in (28, 360, 20, 0):
                ui.pos=(0,bottom);ui.size=(390,844-bottom-32)
                yield from self.frames(5)
                expected=ui.tab_bar.y+ui.tab_bar.height-dp(1)
                assert abs(ui.tab_divider.pos[1]-expected)<.1, (ui.tab_divider.pos,expected)
                assert ui.tab_divider.size==(ui.tab_bar.width,dp(1))
            ui.export_to_png(str(out/f'divider-{destination}.png'))
        ui.pos=(0,0);ui.size=Window.size;ui.size_hint=(1,1)
        self.checked('tab divider follows the actual tab bar through safe-area/keyboard moves on all four pages')
        for width in (320,390):
            Window.size=(width,844)
            for destination in ('library','results','alerts','settings'):
                ui.select_tab(destination)
                yield from self.frames(12)
                assert ui.manager.current==destination
                assert ui.manager.y>=ui.tab_bar.top
                assert len(ui.tab_buttons)==4
                assert all(button.width>=dp(44) for button in ui.tab_buttons.values())
                ui.export_to_png(str(out/f'{destination}-{width}.png'))
        Window.size=(390,844)
        ui.select_tab('results')
        yield from self.frames(12)
        ui.content.export_to_png(str(out/'results-full-390.png'))
        ui.select_tab('settings')
        yield from self.frames(12)
        ui.settings_content.export_to_png(str(out/'settings-full-390.png'))
        ui.appearance_buttons['light'].dispatch('on_release')
        yield from self.frames()
        assert tuple(ui.page_titles['library'].color)==mapped(TEXT)
        assert Window.clearcolor==list(mapped(BG))
        assert mapped(TEXT)[0]<.2
        ui.export_to_png(str(out/'settings-light.png'))
        ui.appearance_buttons['dark'].dispatch('on_release')
        yield from self.frames()
        assert tuple(ui.page_titles['library'].color)==TEXT
        ui.select_tab('results')
        yield from self.frames()
        ui.show_rename_line()
        yield from self.frames()
        assert len(ui.edit_line_colors)==12
        ui.rename_editor.text='Crosspoint research'
        ui.edit_line_colors[2].dispatch('on_release')
        ui.rename_save_button.dispatch('on_release')
        yield from self.frames()
        line=ui.model.current_saved_line()
        assert line.custom_name=='Crosspoint research'
        assert ui.model.store.color_index(line.counter,line.scenario,line.period)==-3
        assert ui.inline_lines.height>dp(44)
        assert not hasattr(ui,'contact_editor')
        # 0.14.1 per-line signal types on the Alerts tab.
        ui.select_tab('alerts')
        yield from self.frames()
        if not line.push_enabled:
            ui.model.store.set_notifications(line.id,'phone',True)
            ui.refresh()
            yield from self.frames()
        for kind in ('buy','monitor','monitor_start'):
            assert (line.id,kind) in ui.alert_switches
            assert ui.alert_switches[(line.id,kind)].width>=dp(44) and ui.alert_switches[(line.id,kind)].height>=dp(44)
        ui.alert_switches[(line.id,'buy')].dispatch('on_release')
        yield from self.frames()
        stored=ui.model.store.get_line(line.id)
        assert not stored.alert_buy and stored.alert_monitor and stored.alert_start
        assert not ui.alert_switches[(line.id,'buy')].active
        ui.alert_switches[(line.id,'phone')].active=False
        yield from self.frames()
        assert ui.alert_switches[(line.id,'monitor')].disabled
        ui.export_to_png(str(out/'alerts-line-types.png'))
        self.checked('four reachable tabs at 320/390 widths, theme contrast, combined name/colour persistence, inline saved lines, per-line signal types and disabled unconfigured signup')

if __name__=='__main__':
    app=RedesignSmoke();app.run();temporary.cleanup()
    raise SystemExit(1 if app.failed else 0)
