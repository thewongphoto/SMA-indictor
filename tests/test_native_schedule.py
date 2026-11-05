import configparser
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import xml.etree.ElementTree as ET
from unittest import TestCase


class NativeSchedulePackagingTests(TestCase):
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
            self.assertEqual(len(app.findall("service")),1)
            self.assertEqual(app.get(f"{{{module.ANDROID}}}label"),"Original")
            self.assertEqual(app.find("service").get(f"{{{module.ANDROID}}}foregroundServiceType"),"dataSync")
            self.assertIsNotNone(app.find("activity"))
            self.assertEqual(path.read_bytes(),(root/"AndroidManifest.xml").read_bytes())

    def test_native_job_packages_headless_entry_and_android14_permissions(self):
        config=configparser.ConfigParser()
        config.read(Path(__file__).parents[1]/"buildozer.spec")
        app=config["app"]
        self.assertEqual(app["services"],"Smaalerts:service/alerts.py")
        self.assertEqual(app["p4a.hook"],"android/p4a_hook.py")
        self.assertIn("androidx.work:work-runtime:2.10.1",app["android.gradle_dependencies"])
        self.assertIn("FOREGROUND_SERVICE_DATA_SYNC",app["android.permissions"])
