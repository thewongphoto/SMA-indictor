import configparser
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock,patch
import json
import sys
import xml.etree.ElementTree as ET
from unittest import TestCase


class NativeSchedulePackagingTests(TestCase):
    def test_delayed_native_events_sort_by_event_time_in_the_visible_request_log(self):
        from sma_analyzer.market_cache import MarketCache
        with TemporaryDirectory() as directory:
            cache=MarketCache(Path(directory)/'market.sqlite3')
            cache.operation('health','VOO','ok',now=1000)
            cache.operation('notification-scheduler','US','failed','Imported later',now=500)
            cache.operation('health','VOO','started',now=1000)
            events=cache.diagnostic_events()
            self.assertEqual([event['at'] for event in events],[1000,1000,500])
            self.assertEqual([event['status'] for event in events],['started','ok','failed'])

    def test_android_scheduler_events_are_imported_with_original_time_and_stage(self):
        from sma_analyzer.native_schedule import sync_schedules
        from sma_analyzer.notifications import NotificationSettings
        store=Mock(path=Path('/private/app/saved_lines.sqlite3'))
        store.notification_settings.return_value=NotificationSettings()
        store.list_all_lines.return_value=[]
        provider=SimpleNamespace(cache=Mock())
        bridge=Mock()
        bridge.configure.return_value='Scheduled'
        bridge.takeEvents.return_value=json.dumps([{'job':'US','status':'failed','at':123000,
            'detail':'Android API 35; stage bind-python-service; SecurityException.'}])
        bridge.takeLastError.return_value=''
        activity=object()
        def autoclass(name):
            return bridge if name.endswith('SmaAlertBridge') else SimpleNamespace(mActivity=activity)
        with patch.dict(sys.modules,{'jnius':SimpleNamespace(autoclass=autoclass)}):
            status=sync_schedules(store,provider,'android')
        self.assertIn('stage bind-python-service',status)
        provider.cache.operation.assert_called_once_with('notification-scheduler','US','failed',
            'Android API 35; stage bind-python-service; SecurityException.',now=123)
        config=json.loads(bridge.configure.call_args.args[1])
        self.assertEqual(config['schema'],2)
        self.assertEqual(set(config['schedules']),{'US','SG','US_START','SG_START'})

    def test_manifest_hook_is_idempotent_and_preserves_existing_application(self):
        module_path=Path(__file__).parents[1]/"android/p4a_hook.py"
        spec=importlib.util.spec_from_file_location("sma_p4a_hook",module_path)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as temp:
            root=Path(temp)
            path=root/"src/main/AndroidManifest.xml"
            path.parent.mkdir(parents=True)
            path.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="org.thewongphoto.smaanalyzer"><application android:label="Original"><activity android:name="Existing"/></application></manifest>')
            (root/"AndroidManifest.xml").write_bytes(path.read_bytes())
            tool=SimpleNamespace(_dist=SimpleNamespace(dist_dir=str(root)))
            module.after_apk_build(tool)
            module.after_apk_build(tool)
            app=ET.parse(path).getroot().find("application")
            services=[node for node in app.findall("service")
                      if node.get(f"{{{module.TOOLS}}}node")!="remove"]
            self.assertEqual(len(services),1)
            self.assertEqual(app.get(f"{{{module.ANDROID}}}label"),"Original")
            service=services[0]
            self.assertEqual(service.get(f"{{{module.ANDROID}}}name"),"org.thewongphoto.smaanalyzer.SmaBackgroundService")
            self.assertEqual(service.get(f"{{{module.ANDROID}}}process"),":sma_background_alerts")
            self.assertEqual(service.get(f"{{{module.ANDROID}}}exported"),"false")
            self.assertEqual(service.get(f"{{{module.ANDROID}}}stopWithTask"),"false")
            self.assertIsNotNone(app.find("activity"))
            for attribute in ("debuggable","allowBackup","fullBackupContent","usesCleartextTraffic"):
                self.assertEqual(app.get(f"{{{module.ANDROID}}}{attribute}"),"false")
            foreground=[node for node in app.findall("service") if node.get(f"{{{module.ANDROID}}}name")==
                        "androidx.work.impl.foreground.SystemForegroundService"]
            self.assertEqual(len(foreground),1)
            self.assertEqual(foreground[0].get(f"{{{module.TOOLS}}}node"),"remove")
            self.assertEqual(path.read_bytes(),(root/"AndroidManifest.xml").read_bytes())

    def test_native_job_packages_private_bound_entry_without_foreground_permissions(self):
        config=configparser.ConfigParser()
        config.read(Path(__file__).parents[1]/"buildozer.spec")
        app=config["app"]
        self.assertEqual(app["services"],"Smaalerts:service/alerts.py")
        self.assertEqual(app["p4a.hook"],"android/p4a_hook.py")
        self.assertIn("androidx.work:work-runtime:2.10.1",app["android.gradle_dependencies"])
        self.assertNotIn("FOREGROUND_SERVICE",app["android.permissions"])
        self.assertIn("WAKE_LOCK",app["android.permissions"])
        self.assertIn("RECEIVE_BOOT_COMPLETED",app["android.permissions"])
