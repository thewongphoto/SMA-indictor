import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from sma_analyzer.notifications import Alert, AndroidNotifier


class AndroidNotificationTests(TestCase):
    def setUp(self):
        self.alert = Alert('phone','buy','DEMO-SGX','Trending',11,12,100,'Buy Signal','SIMULATED TEST')
        self.sdk = SimpleNamespace(SDK_INT=35)
        self.manager = Mock()
        self.manager.areNotificationsEnabled.return_value = True
        self.activity = Mock()
        self.activity.getSystemService.return_value = self.manager
        self.activity.checkSelfPermission.return_value = 0
        self.activity.getResources.return_value.getIdentifier.return_value = 123
        self.builder = Mock()
        self.builder.build.return_value = 'notification'
        self.pending = Mock(FLAG_UPDATE_CURRENT=1,FLAG_IMMUTABLE=2)
        self.classes = {
            'org.kivy.android.PythonActivity':SimpleNamespace(mActivity=self.activity),
            'android.os.Build$VERSION':self.sdk,
            'android.content.Context':SimpleNamespace(NOTIFICATION_SERVICE='notifications'),
            'android.app.NotificationChannel':Mock(),
            'android.app.Notification$Builder':Mock(return_value=self.builder),
            'android.app.Notification$BigTextStyle':Mock(),
            'android.app.PendingIntent':self.pending,
            'android.R$drawable':SimpleNamespace(stat_notify_more=88),
        }
        self.jnius = ModuleType('jnius')
        self.jnius.autoclass = lambda name:self.classes[name]
        self.jnius.cast = lambda name,instance:instance
        self.permissions = ModuleType('android.permissions')
        self.permissions.check_permission = Mock(return_value=False)
        self.permissions.request_permissions = Mock()
        self.android = ModuleType('android')
        runnable = ModuleType('android.runnable')
        runnable.run_on_ui_thread = lambda function:function
        self.modules = patch.dict(sys.modules,{'jnius':self.jnius,'android':self.android,'android.permissions':self.permissions,'android.runnable':runnable})
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def test_android13_permission_callback_and_denial(self):
        result = Mock()
        AndroidNotifier.request_permission(result)
        args,_ = self.permissions.request_permissions.call_args
        self.assertEqual(args[0],['android.permission.POST_NOTIFICATIONS'])
        result.assert_not_called()
        args[1](args[0],[False])
        result.assert_called_once_with(False)

    def test_old_or_already_granted_permission_continues_immediately(self):
        for sdk,granted in ((32,False),(35,True)):
            self.sdk.SDK_INT = sdk
            self.permissions.check_permission.return_value = granted
            result = Mock()
            AndroidNotifier.request_permission(result)
            result.assert_called_once_with(True)
        self.permissions.request_permissions.assert_not_called()

    def test_channel_icon_content_and_tap_intent(self):
        notifier = AndroidNotifier()
        notifier.send(self.alert)
        self.manager.createNotificationChannel.assert_called_once()
        self.builder.setSmallIcon.assert_called_once_with(123)
        self.builder.setContentTitle.assert_called_once_with(self.alert.subject)
        self.builder.setContentText.assert_called_once_with(self.alert.body)
        self.builder.setContentIntent.assert_called_once()
        args,_ = self.pending.getActivity.call_args
        self.assertEqual(args[-1],3)
        first = self.manager.notify.call_args.args[0]
        notifier.send(self.alert)
        self.assertEqual(first,self.manager.notify.call_args.args[0])

    def test_denied_permission_posts_nothing(self):
        self.activity.checkSelfPermission.return_value = -1
        with self.assertRaisesRegex(RuntimeError,'Allow notifications'): AndroidNotifier().send(self.alert)
        self.manager.notify.assert_not_called()

    def test_disabled_notifications_and_icon_fallback(self):
        self.manager.areNotificationsEnabled.return_value = False
        with self.assertRaisesRegex(RuntimeError,'disabled'): AndroidNotifier().send(self.alert)
        self.manager.notify.assert_not_called()
        self.manager.areNotificationsEnabled.return_value = True
        self.activity.getResources.return_value.getIdentifier.return_value = 0
        AndroidNotifier().send(self.alert)
        self.builder.setSmallIcon.assert_called_once_with(88)

    def test_disabled_alert_channel_is_reported(self):
        self.manager.getNotificationChannel.return_value = SimpleNamespace(getImportance=lambda:0)
        with self.assertRaisesRegex(RuntimeError,'channel is disabled'): AndroidNotifier().send(self.alert)
        self.manager.notify.assert_not_called()
