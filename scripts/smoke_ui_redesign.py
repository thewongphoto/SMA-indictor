"""Four-tab navigation, appearance, line editing and narrow layouts."""
from pathlib import Path
from kivy.core.window import Window
from kivy.metrics import dp
from scripts.smoke_ui_flow import FlowSmoke, temporary
from sma_analyzer.appearance import mapped
from sma_analyzer.theme import TEXT, BG


class RedesignSmoke(FlowSmoke):
    def steps(self):
        yield from super().steps()
        ui=self.screen
        out=Path('artifacts/redesign-ui');out.mkdir(parents=True,exist_ok=True)
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
        self.checked('four reachable tabs at 320/390 widths, theme contrast, combined name/colour persistence, inline saved lines and disabled unconfigured signup')

if __name__=='__main__':
    app=RedesignSmoke();app.run();temporary.cleanup()
    raise SystemExit(1 if app.failed else 0)
