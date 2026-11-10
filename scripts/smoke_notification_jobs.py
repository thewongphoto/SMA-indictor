"""Notification settings/queue UI over controlled HTTP and native-bridge fixtures.

This does not prove physical Android delivery. The in-app background test uses
the actual WorkManager/bound-service path after installing the built APK.
"""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

from kivy.core.window import Window
from kivy.uix.label import Label

from scripts.smoke_mobile_yahoo_ui import MobileYahooSmoke,temporary


class NotificationJobsSmoke(MobileYahooSmoke):
    def build(self):
        self.bridge=Mock()
        self.bridge.testBackground.return_value='Background notification test queued. Put the app in the background, then check the notification and data request log.'
        self.context=object()
        self.permission_allowed=True
        def permission(callback):
            callback(self.permission_allowed)
        def autoclass(name):
            if name.endswith('SmaAlertBridge'):
                return self.bridge
            assert name=='org.kivy.android.PythonActivity',name
            return SimpleNamespace(mActivity=self.context)
        self.patches=[patch('sma_analyzer.app.platform','android'),
            patch('sma_analyzer.native_schedule.sync_schedules',return_value='Closing checks and enabled opening reminders scheduled. Android may delay a check while sleeping or offline.'),
            patch('sma_analyzer.app.AndroidNotifier.request_permission',side_effect=permission),
            patch.dict('sys.modules',{'jnius':SimpleNamespace(autoclass=autoclass)})]
        for item in self.patches:
            item.start()
        return super().build()

    def frames(self,count=8):
        for _ in range(count):
            yield lambda:True

    def steps(self):
        ui=self.screen
        yield lambda:not ui._source_check_busy
        ui.show_settings()
        yield from self.frames()
        assert set(ui.notification_switches)=={'phone_buy','phone_monitor','phone_monitor_start'}
        assert all(switch.active for switch in ui.notification_switches.values())
        text=' '.join(widget.text for widget in ui.settings_panel.walk() if isinstance(widget,Label))
        assert 'Impending buy signal (End of trading)' in text
        assert 'Impending buy signal (Start of trading)' in text
        assert '9:30pm' in text and '9am' in text and '6:30am' in text and '6:30pm' in text
        assert 'strictly below the last adjusted closing price' in text
        self.checked('all three persisted signal switches default On; fixed SGT times and distinct closing/opening conditions are visible')
        directory=Path('artifacts/notifications-0.13.0')
        directory.mkdir(parents=True,exist_ok=True)
        for width in (320,440):
            Window.size=(width,920)
            yield from self.frames()
            assert all(switch.width>=44 and switch.height>=44 for switch in ui.notification_switches.values())
            ui.settings_panel.export_to_png(str(directory/f'settings-{width}.png'))
        calls=len(self.client.calls)
        ui.background_test_button.dispatch('on_release')
        yield from self.frames()
        self.bridge.testBackground.assert_called_once_with(self.context)
        assert 'queued' in ui.notification_status.text
        assert any(event['operation']=='notification-test-background' and event['status']=='requested'
                   for event in self.cache.diagnostic_events())
        self.permission_allowed=False
        ui.background_test_button.dispatch('on_release')
        yield from self.frames()
        self.bridge.testBackground.assert_called_once()
        assert 'Allow Android notifications' in ui.notification_status.text
        self.permission_allowed=True
        self.bridge.testBackground.side_effect=RuntimeError('private device identifier')
        ui.background_test_button.dispatch('on_release')
        yield from self.frames()
        assert 'private device identifier' not in json.dumps(self.cache.diagnostic_events())
        assert any(event['operation']=='notification-test-background' and event['status']=='failed'
                   for event in self.cache.diagnostic_events())
        ui.notification_switches['phone_monitor_start'].active=False
        settings=ui.model.store.notification_settings()
        assert not settings.phone_monitor_start and settings.phone_buy and settings.phone_monitor
        assert len(self.client.calls)==calls
        self.checked('background test queues the native bridge after permission, reports denial/failure safely and makes no market request')
        self.checked('opening reminder switch persists independently of both closing signals')

    def on_stop(self):
        self.screen.close()
        for item in reversed(self.patches):
            item.stop()
        Path('artifacts/ui-notification-jobs.json').write_text(json.dumps(
            {'passed':not self.failed,'checks':self.checks,
             'scope':'controlled mobile HTTP/native bridge fixtures; physical background delivery needs the APK test'},indent=2))


if __name__=='__main__':
    app=NotificationJobsSmoke()
    app.run()
    temporary.cleanup()
    raise SystemExit(1 if app.failed else 0)
