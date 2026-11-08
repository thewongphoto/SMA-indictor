import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import sys
from unittest import TestCase
from unittest.mock import Mock, patch

from sma_analyzer.android_window import WindowMetrics
from sma_analyzer import ios_runtime as ios
from sma_analyzer.notifications import Alert, NotificationPresentation, deliver_alerts
from sma_analyzer.storage import LineStore


class IOSRuntimeTests(TestCase):
    def setUp(self):
        self.native = Mock()
        self.native.deliveryResult_.return_value = json.dumps({"status":"ok"})
        self.native.postAlertJSON_.return_value = "receipt"
        self.addCleanup(patch.stopall)
        patch.object(ios,"bridge",return_value=self.native).start()
        patch.object(ios,"ns_string",side_effect=lambda value:value).start()
        self.alert = Alert("phone","buy","YAHOO:VOO","Adjusted daily close",28,12,100,
                           "Recovery signal", "Example", "2026-11-05", "yahoo")

    def test_banner_sound_center_and_stable_event_identity_cross_native_boundary(self):
        receipt = ios.IOSNotifier().send(self.alert)
        payload = json.loads(self.native.postAlertJSON_.call_args.args[0])
        self.assertTrue(payload["banner"] and payload["sound"] and payload["list"])
        self.assertEqual((payload["title"],payload["body"]),(self.alert.subject,self.alert.body))
        self.assertEqual(len(payload["id"]),64)
        self.assertIn("iOS settings and Focus",receipt)

    def test_explicit_quiet_presentation_is_preserved(self):
        from dataclasses import replace
        ios.IOSNotifier().send(replace(self.alert,presentation=NotificationPresentation(False,False,True)))
        payload = json.loads(self.native.postAlertJSON_.call_args.args[0])
        self.assertFalse(payload["banner"] or payload["sound"])
        self.assertTrue(payload["list"])

    def test_os_denial_does_not_record_delivery_or_hide_failure(self):
        self.native.deliveryResult_.return_value = json.dumps({"status":"failed","detail":"Allow notifications in iPhone Settings."})
        with TemporaryDirectory() as directory:
            store = LineStore(Path(directory)/"lines.sqlite3")
            cache = Mock()
            report = deliver_alerts(store,[self.alert],ios.IOSNotifier(),cache=cache)
            self.assertFalse(store.was_delivered(self.alert.key))
            self.assertIn("Allow notifications",report[0])
            self.assertEqual(cache.operation.call_args.args[2],"failed")

    def test_default_ios_delivery_logs_correct_os_and_deduplicates(self):
        with TemporaryDirectory() as directory, patch.dict("os.environ",{"KIVY_BUILD":"ios"}):
            store = LineStore(Path(directory)/"lines.sqlite3")
            report = deliver_alerts(store,[self.alert])
            self.assertIn("Posted to iOS",report[0])
            self.assertTrue(store.was_delivered(self.alert.key))
            deliver_alerts(store,[self.alert])
            self.native.postAlertJSON_.assert_called_once()

    def test_expired_background_task_never_posts(self):
        self.native.taskActive_.return_value = False
        with self.assertRaisesRegex(RuntimeError,"ended this background check"):
            ios.IOSNotifier("expired-token").send(self.alert)
        self.native.postAlertJSON_.assert_not_called()

    def test_permission_callback_waits_for_native_result_and_finishes_once(self):
        clock = Mock()
        callback = Mock()
        with patch.dict(sys.modules,{"kivy.clock":SimpleNamespace(Clock=clock)}):
            ios.IOSNotifier.request_permission(callback)
        poll = clock.schedule_interval.call_args.args[0]
        self.native.permissionResult.return_value = -1
        self.assertTrue(poll(0))
        callback.assert_not_called()
        self.native.permissionResult.return_value = 1
        self.assertFalse(poll(0))
        callback.assert_called_once_with(True)

    def test_window_rescales_native_points_without_double_counting_home_indicator(self):
        clock = Mock()
        callback = Mock()
        self.native.windowMetricsJSON.return_value = json.dumps({"width":390,"height":844,"left":0,"right":0,
            "top":47,"bottom":34,"keyboard":0})
        adapter = ios.IOSWindow()
        with patch.dict(sys.modules,{"kivy.clock":SimpleNamespace(Clock=clock)}):
            adapter.start(callback)
        metrics = callback.call_args.args[0]
        self.assertEqual(metrics.content_bounds(1170,2532),(0,102,1170,2289))
        callback.reset_mock()
        poll = clock.schedule_interval.call_args.args[0]
        poll(0)
        callback.assert_not_called()
        self.native.windowMetricsJSON.return_value = json.dumps({"width":390,"height":844,"top":47,"bottom":34,"keyboard":290})
        poll(0)
        self.assertEqual(callback.call_args.args[0].content_bounds(1170,2532),(0,870,1170,1521))
        adapter.stop()
        clock.schedule_interval.return_value.cancel.assert_called_once()

    def test_scheduler_logs_native_unavailability_instead_of_claiming_exact_execution(self):
        config = {"directory":"/app/Documents", "regions":["US"], "schedules":{}}
        self.native.configureJSON_.return_value = json.dumps({"status":"unavailable","detail":"Background App Refresh is unavailable."})
        cache = Mock()
        with patch.object(ios.Path,"home",return_value=Path("/app")):
            self.assertIn("unavailable",ios.sync_ios_schedules(config,cache))
        self.assertEqual(json.loads(self.native.configureJSON_.call_args.args[0]),
                         dict(config,directory="Documents",directory_base="application-home"))
        cache.operation.assert_called_once_with("notification-scheduler","iOS","unavailable","Background App Refresh is unavailable.")

    def test_app_update_relocates_sandbox_without_losing_the_background_cache_location(self):
        config=ios.portable_configuration({"directory":"/sandbox/old-uuid/Documents/smastockanalyzer"},home="/sandbox/old-uuid")
        self.assertEqual(ios.configured_directory(config,home="/sandbox/new-uuid"),
                         Path("/sandbox/new-uuid/Documents/smastockanalyzer"))
        self.assertNotIn("old-uuid",json.dumps(config))

    def test_background_data_path_cannot_escape_the_signed_app_container(self):
        with self.assertRaises(RuntimeError):
            ios.portable_configuration({"directory":"/other-app/Documents"},home="/this-app")
        with self.assertRaises(RuntimeError):
            ios.configured_directory({"directory":"../../other-app","directory_base":"application-home"},home="/this-app")

    def test_cold_background_launch_pumps_native_events_without_importing_kivy(self):
        self.native.isBackground.side_effect=[True,True,False]
        with patch.dict(sys.modules,{"kivy":None,"kivy.core.window":None}), patch.object(ios.time,"sleep") as sleep:
            ios.wait_for_foreground()
        self.native.start.assert_called_once()
        self.native.pumpEvents.assert_called_once()
        sleep.assert_called_once_with(.02)

    def test_loading_shared_entry_point_does_not_initialize_a_window(self):
        import runpy
        with patch.dict(sys.modules,{"sma_analyzer.app":None}):
            entry=runpy.run_path(str(Path(__file__).resolve().parents[1]/"main.py"),run_name="entry_test")
        self.assertTrue(callable(entry["run"]))
