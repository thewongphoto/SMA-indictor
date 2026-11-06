import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from sma_analyzer.notifications import Alert, AndroidNotifier, RESEARCH_CHANNEL_ID, LEGACY_RESEARCH_CHANNEL_ID


class AndroidNotificationTests(TestCase):
    def setUp(self):
        self.alert = Alert('phone','buy','DEMO-SGX','Trending',11,12,100,'Buy Signal','SIMULATED TEST')
        self.sdk = SimpleNamespace(SDK_INT=35)
        self.manager = Mock()
        self.manager.areNotificationsEnabled.return_value = True
        self.manager.getNotificationChannel.return_value = None
        self.channel=Mock()
        self.channel.getImportance.return_value=4
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
            'android.app.NotificationChannel':Mock(return_value=self.channel),
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

    def test_headless_service_context_posts_without_a_live_activity(self):
        self.classes['org.kivy.android.PythonActivity'].mActivity=None
        AndroidNotifier(context=self.activity).send(self.alert)
        self.manager.notify.assert_called_once()
        self.classes['android.app.Notification$Builder'].assert_called_once_with(self.activity,RESEARCH_CHANNEL_ID)

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

    def legacy_channel(self,importance=3,user_selected=False):
        legacy=Mock()
        legacy.getImportance.return_value=importance
        legacy.hasUserSetImportance.return_value=user_selected
        self.manager.getNotificationChannel.side_effect=lambda identity:legacy if identity==LEGACY_RESEARCH_CHANNEL_ID else None
        return legacy

    def test_upgrade_from_default_quiet_channel_creates_high_importance_banner_channel(self):
        self.legacy_channel()
        receipt=AndroidNotifier().send(self.alert)
        self.classes['android.app.NotificationChannel'].assert_called_once_with(RESEARCH_CHANNEL_ID,'SMA signal alerts',4)
        self.channel.enableVibration.assert_called_once_with(True)
        self.classes['android.app.Notification$Builder'].assert_called_once_with(self.activity,RESEARCH_CHANNEL_ID)
        self.assertIn('Banner and sound requested',receipt)
        self.builder.setAutoCancel.assert_called_once_with(True)

    def test_explicitly_silenced_legacy_channel_is_not_bypassed(self):
        for importance,chosen in ((2,False),(3,True)):
            with self.subTest(importance=importance,user_chosen=chosen):
                self.legacy_channel(importance,chosen)
                receipt=AndroidNotifier().send(self.alert)
                self.assertIn('existing quiet channel',receipt)
                self.classes['android.app.Notification$Builder'].assert_called_with(self.activity,LEGACY_RESEARCH_CHANNEL_ID)
        self.manager.createNotificationChannel.assert_not_called()

    def test_disabled_legacy_channel_is_not_bypassed_on_upgrade(self):
        self.legacy_channel(0)
        with self.assertRaisesRegex(RuntimeError,'channel is disabled'):
            AndroidNotifier().send(self.alert)
        self.manager.createNotificationChannel.assert_not_called()
        self.manager.notify.assert_not_called()

    def test_existing_banner_channel_and_user_overrides_are_retained(self):
        self.manager.getNotificationChannel.return_value=self.channel
        self.channel.getImportance.return_value=3
        receipt=AndroidNotifier().send(self.alert)
        self.manager.createNotificationChannel.assert_not_called()
        self.assertIn('existing quiet channel',receipt)
        self.classes['android.app.Notification$Builder'].assert_called_once_with(self.activity,RESEARCH_CHANNEL_ID)

    def test_pre_channel_adapter_requests_high_priority_sound_and_retains_center_entry(self):
        self.sdk.SDK_INT=25
        AndroidNotifier().send(self.alert)
        self.builder.setPriority.assert_called_once_with(1)
        self.builder.setDefaults.assert_called_once_with(3)
        self.builder.setAutoCancel.assert_called_once_with(True)
        self.assertTrue(self.alert.presentation.banner and self.alert.presentation.sound and self.alert.presentation.notification_center)
