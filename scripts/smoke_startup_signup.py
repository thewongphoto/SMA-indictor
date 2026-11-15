"""First rendered welcome never waits for email readiness or Yahoo retrieval."""
import os
from pathlib import Path
import subprocess
import sys

# A separate process gives each case a real cold Kivy lifecycle and fresh store.
if __name__ == '__main__' and len(sys.argv) == 1:
    for scenario in ('first', 'returning', 'disabled'):
        subprocess.run([sys.executable, '-m', 'scripts.smoke_startup_signup', scenario], check=True)
    raise SystemExit(0)

import json
from threading import Event
from unittest.mock import patch
# Match the real entry point: configure/create Kivy through app.py before any
# test imports Window. Resizing an already-created SDL surface during build
# makes first-frame readbacks invalid under the offscreen software backend.
from sma_analyzer.app import AnalyzerScreen
from kivy.core.window import Window
from kivy.clock import Clock
from scripts.smoke_mobile_yahoo_ui import MobileYahooSmoke, temporary
from sma_analyzer.storage import LineStore

OUT = Path('artifacts/startup-signup')


class StartupSignupSmoke(MobileYahooSmoke):
    def build(self):
        self.scenario = sys.argv[1]
        OUT.mkdir(parents=True, exist_ok=True)
        for capture in OUT.glob(self.scenario + '-first-frame*.png'): capture.unlink()
        self.email_gate, self.email_entered = Event(), Event()
        self.market_gate, self.market_entered = Event(), Event()
        self.capability_result = True
        self.first_frame = None
        self.patches = [
            patch.dict(os.environ, {'SMA_CONTACT_BASE_URL': '' if self.scenario == 'disabled' else 'https://fixture.example'}),
            patch('sma_analyzer.contact.capabilities', side_effect=self.capabilities),
            patch('sma_analyzer.contact.submit', return_value='volunteer@example.com'),
        ]
        self.mocks = [p.start() for p in self.patches]
        if self.scenario == 'returning':
            store = LineStore(Path(temporary.name) / 'saved_lines.sqlite3')
            with store._connect() as db:
                db.execute("INSERT INTO preferences VALUES ('release_contact_seen','true')")
                db.execute("INSERT INTO preferences VALUES ('release_contact_email','\"existing@example.com\"')")
        root = super().build()
        # A pending market operation must not prevent readiness or email sending.
        self.screen.market_executor.submit(self.hold_market)
        Window.bind(on_flip=self.observe_first_frame)
        return root

    def hold_market(self):
        self.market_entered.set()
        assert self.market_gate.wait(60), 'Fixture market gate was not released'

    def capabilities(self):
        self.email_entered.set()
        assert self.email_gate.wait(60), 'Fixture email gate was not released'
        if isinstance(self.capability_result, Exception): raise self.capability_result
        return self.capability_result

    def observe_first_frame(self, *_):
        if self.first_frame is not None: return
        popup = getattr(self.screen, 'welcome_popup', None)
        self.first_frame = dict(welcome_open=bool(popup and popup._is_open),
                                welcome_alpha=popup._anim_alpha if popup else None,
                                welcome_topmost=bool(popup and Window.children[0] is popup),
                                email_check_finished=getattr(self.screen, 'contact_available', None) is not None)
        Window.screenshot(name=str(OUT / (self.scenario + '-first-frame.png')))

    def frames(self, count=5):
        for _ in range(count): yield lambda: True

    def steps(self):
        ui = self.screen
        yield lambda: self.first_frame is not None
        if self.scenario == 'disabled':
            assert not self.first_frame['welcome_open']
            assert not hasattr(ui, 'contact_editor')
            self.mocks[1].assert_not_called()
            self.checked('explicitly disabled email endpoint makes no request and opens Home')
            return
        yield lambda: self.email_entered.is_set() and self.market_entered.is_set()
        assert not self.first_frame['email_check_finished']
        if self.scenario == 'returning':
            assert not self.first_frame['welcome_open']
            assert not hasattr(ui, 'welcome_popup')
            assert ui.contact_editor.text == 'existing@example.com'
            self.email_gate.set()
            yield lambda: ui.contact_available is True
            assert not hasattr(ui, 'welcome_popup')
            self.checked('returning user opens Home without waiting, keeps email, and sees no late invitation')
            return
        assert self.first_frame['welcome_open'], self.first_frame
        assert self.first_frame['welcome_alpha'] == 1, self.first_frame
        assert self.first_frame['welcome_topmost'], self.first_frame
        assert ui.welcome_continue.disabled and not ui.welcome_skip.disabled
        assert not ui.welcome_editor.disabled
        ui.welcome_editor.text = 'volunteer@example.com'
        ui.welcome_editor.dispatch('on_text_validate')
        self.mocks[2].assert_not_called()
        self.checked('first rendered frame is the full welcome; typing and Skip work while both network checks are held')
        ui.welcome_skip.dispatch('on_release')
        assert not ui.welcome_popup._is_open
        ui.show_search()
        self.email_gate.set()
        yield lambda: ui.contact_available is True
        assert ui.manager.current == 'search' and not ui.welcome_popup._is_open
        with ui.model.store._connect() as db:
            assert db.execute("SELECT value FROM preferences WHERE key='release_contact_seen'").fetchone()[0] == 'true'
        self.checked('Skip persists immediately; a late readiness reply never interrupts Search or sends an email')
        # An offline/failed check cannot block the UI; retries preserve input.
        self.capability_result = OSError('fixture offline')
        ui.check_signup_service()
        yield lambda: ui.contact_available is False
        ui.show_welcome()
        assert ui.welcome_continue.disabled and ui.welcome_check.parent is ui.welcome_messages
        ui.welcome_editor.text = 'volunteer@example.com'
        ui.welcome_editor.dispatch('on_text_validate')
        self.mocks[2].assert_not_called()
        self.capability_result = True
        ui.welcome_check.dispatch('on_release')
        yield lambda: ui.contact_available is True
        assert ui.welcome_editor.text == 'volunteer@example.com'
        assert not ui.welcome_continue.disabled
        assert ui.welcome_check.parent is None
        ui.welcome_continue.dispatch('on_release')
        yield lambda: not ui.contact_sending
        assert ui.welcome_continue.text == 'Open the app'
        assert ui.contact_editor.text == 'volunteer@example.com'
        self.mocks[2].assert_called_once()
        assert not self.market_gate.is_set()
        ui.welcome_continue.dispatch('on_release')
        assert not ui.welcome_popup._is_open
        ui.check_signup_service()
        yield lambda: ui.contact_available is True
        assert not ui.welcome_popup._is_open
        self.checked('offline setup retries preserve input, sending waits for readiness and bypasses the blocked market worker; no welcome reopens')

    def on_stop(self):
        Window.unbind(on_flip=self.observe_first_frame)
        self.screen.close()
        self.email_gate.set()
        self.market_gate.set()
        for p in reversed(self.patches): p.stop()
        (OUT / (self.scenario + '.json')).write_text(json.dumps(dict(passed=not self.failed,
            first_frame=self.first_frame, checks=self.checks,
            scope='actual Kivy first frame; held HTTP fixtures, no phone timing or real email'), indent=2))


if __name__ == '__main__':
    app = StartupSignupSmoke()
    app.run()
    temporary.cleanup()
    raise SystemExit(1 if app.failed else 0)
