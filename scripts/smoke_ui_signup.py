"""Welcome screen handles failed/confirmed submissions without real email."""
from concurrent.futures import Future
from unittest.mock import patch
from pathlib import Path
from kivy.core.window import Window
from scripts.smoke_ui_flow import FlowSmoke,temporary

class SignupSmoke(FlowSmoke):
    def steps(self):
        yield from super().steps()
        ui=self.screen
        ready=Future();ready.set_result(True);ui.signup_ready(ready)
        yield from self.frames(12)
        assert ui.welcome_popup._is_open
        out=Path('artifacts/signup-ui');out.mkdir(parents=True,exist_ok=True)
        Window.size=(390,844)
        yield from self.frames(8)
        ui.welcome_popup.export_to_png(str(out/'welcome.png'))
        ui.welcome_editor.text='invalid'
        ui.welcome_continue.dispatch('on_release')
        assert 'valid email' in ui.welcome_status.text.lower()
        assert ui.welcome_popup._is_open
        def fail(*args):raise ValueError('Fixture email service rejected the request.')
        with patch('sma_analyzer.contact.submit',side_effect=fail):
            ui.welcome_editor.text='volunteer@example.com'
            ui.welcome_continue.dispatch('on_release')
            yield lambda:not ui.contact_submit.disabled
            assert ui.welcome_popup._is_open
            assert 'rejected' in ui.welcome_status.text
            assert ui.welcome_continue.text=='Continue'
        with ui.model.store._connect() as db:
            import json
            pending=json.loads(db.execute("SELECT value FROM preferences WHERE key='release_contact_pending'").fetchone()[0])
        with patch('sma_analyzer.contact.submit',return_value='volunteer@example.com') as send:
            ui.welcome_continue.dispatch('on_release')
            yield lambda:not ui.contact_submit.disabled
            yield from self.frames(3)
            assert ui.welcome_popup._is_open
            assert ui.welcome_continue.text=='Open the app'
            assert send.call_args.args[2]==pending['request_id']
            assert 'forwarded' in ui.welcome_status.text
        ui.welcome_popup.export_to_png(str(out/'welcome-confirmed.png'))
        ui.welcome_continue.dispatch('on_release')
        yield from self.frames()
        assert not ui.welcome_popup._is_open
        with ui.model.store._connect() as db:
            assert db.execute("SELECT value FROM preferences WHERE key='release_contact_email'").fetchone()[0]=='"volunteer@example.com"'
            assert db.execute("SELECT value FROM preferences WHERE key='release_contact_pending'").fetchone() is None
        ui.show_welcome()
        yield from self.frames()
        ui.welcome_skip.dispatch('on_release')
        yield from self.frames()
        assert not ui.welcome_popup._is_open
        self.checked('email welcome validates input, retains failed requests for retry, confirms acceptance before Open, persists email and supports Skip; delivery mocked')

if __name__=='__main__':
    app=SignupSmoke();app.run();temporary.cleanup();raise SystemExit(1 if app.failed else 0)
