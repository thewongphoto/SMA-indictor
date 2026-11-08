import importlib.util
import json
from pathlib import Path
import plistlib
import shutil
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
import xml.etree.ElementTree as ET

from scripts.make_iphone_kit import make_kit
from scripts.prepare_ios import ROOT, configure_info, configure_project, stage_app, APP_VERSION


class IOSPackagingTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def test_staging_allowlist_excludes_personal_data_and_old_build_debris(self):
        source = self.directory/"source"
        (source/"sma_analyzer/assets/logos").mkdir(parents=True)
        for name,value in (("main.py","print('app')"),("sma_analyzer/app.py","# UI"),
                           ("sma_analyzer/cache.sqlite3","private"),("sma_analyzer/token.json","secret"),
                           ("sma_analyzer/assets/logos/brand.png","png"),("sma_analyzer/assets/logos/CREDITS.txt","credits")):
            (source/name).write_text(value)
        destination = self.directory/"stage"
        destination.mkdir()
        (destination/"old-token.json").write_text("must not ship")
        stage_app(destination,source)
        names = {str(file.relative_to(destination)) for file in destination.rglob("*") if file.is_file()}
        self.assertEqual(names,{"main.py","sma_analyzer/app.py","sma_analyzer/assets/logos/brand.png","sma_analyzer/assets/logos/CREDITS.txt"})
        with self.assertRaises(ValueError):
            stage_app(source,source)

    def test_info_allows_supported_free_capabilities_and_expands_the_selected_bundle_id(self):
        info = configure_info({"CFBundleExecutable":"smaanalyzer"})
        self.assertEqual(info["CFBundleShortVersionString"],APP_VERSION)
        self.assertEqual(info["UIBackgroundModes"],["fetch"])
        self.assertEqual(info["CFBundleIdentifier"],"$(PRODUCT_BUNDLE_IDENTIFIER)")
        self.assertTrue(all(value.startswith("$(PRODUCT_BUNDLE_IDENTIFIER).refresh.") for value in info["BGTaskSchedulerPermittedIdentifiers"]))
        self.assertEqual(info["UISupportedInterfaceOrientations"],["UIInterfaceOrientationPortrait"])
        self.assertNotIn("NSAppTransportSecurity",info)

    def fake_app(self, platform="iPhoneOS"):
        app = self.directory/"app.app"
        app.mkdir()
        (app/"Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable":"smaanalyzer","CFBundleSupportedPlatforms":[platform]}))
        (app/"smaanalyzer").write_bytes(b"unsigned compiled fixture; not an installable binary")
        (app/"smaanalyzer").chmod(0o755)
        (app/"embedded.mobileprovision").write_text("private profile must be excluded")
        (app/"YourApp").mkdir()
        (app/"YourApp/main.pyc").write_bytes(b"fixture")
        return app

    def test_kit_preserves_compiled_payload_without_shipping_signing_credentials(self):
        kit = make_kit(self.fake_app(),self.directory/"kit")
        self.assertTrue((kit/"UnsignedApp.app/YourApp/main.pyc").is_file())
        self.assertFalse((kit/"UnsignedApp.app/embedded.mobileprovision").exists())
        self.assertFalse(json.loads((kit/"BUILD_INFO.json").read_text())["signed"])
        self.assertEqual(plistlib.loads((kit/"Info.plist").read_bytes())["CFBundleIdentifier"],"$(PRODUCT_BUNDLE_IDENTIFIER)")
        scheme = ET.parse(kit/"SMA-iPhone.xcodeproj/xcshareddata/xcschemes/smaanalyzer.xcscheme")
        self.assertEqual(scheme.find(".//BuildableReference").attrib["ReferencedContainer"],"container:SMA-iPhone.xcodeproj")
        self.assertIn("--exclude /Info.plist",(kit/"copy-payload.sh").read_text())
        self.assertIn("--exclude /embedded.mobileprovision",(kit/"copy-payload.sh").read_text())

    def test_kit_rejects_a_simulator_app(self):
        with self.assertRaisesRegex(ValueError,"device binary"):
            make_kit(self.fake_app("iPhoneSimulator"),self.directory/"kit")

    @skipUnless(importlib.util.find_spec("pbxproj"),"Install requirements-validation.txt for Xcode project checks")
    def test_generated_project_links_arc_bridge_and_preserves_automatic_personal_signing(self):
        from pbxproj import XcodeProject
        base = self.directory/"smaanalyzer-ios"
        shutil.copytree(ROOT/"ios/signing-template",base)
        (base/"SMA-iPhone.xcodeproj").rename(base/"smaanalyzer.xcodeproj")
        (base/"smaanalyzer-Info.plist").write_bytes(plistlib.dumps({}))
        (base/"main.m").write_text('putenv("IOS_IS_WINDOWED=False");\nputenv("KIVY_BUILD=ios");')
        project = XcodeProject.load(str(configure_project(base)/"project.pbxproj"))
        bridge = next(item for item in project.objects.get_objects_in_section("PBXFileReference") if item.path.endswith("SMAIOSBridge.m"))
        buildfile = next(item for item in project.objects.get_objects_in_section("PBXBuildFile") if item.fileRef==bridge.get_id())
        self.assertEqual(buildfile.settings["COMPILER_FLAGS"].strip(),"-fobjc-arc")
        for config in project.objects.get_objects_in_section("XCBuildConfiguration"):
            self.assertEqual(config.buildSettings["CODE_SIGN_STYLE"],"Automatic")
            self.assertEqual(config.buildSettings["IPHONEOS_DEPLOYMENT_TARGET"],"15.0")
        self.assertIn("IOS_IS_WINDOWED=True",(base/"main.m").read_text())
        self.assertIn("KIVY_NO_ARGS=1",(base/"main.m").read_text())

    @skipUnless(importlib.util.find_spec("yaml"),"Install requirements-validation.txt for workflow checks")
    def test_ci_builds_device_and_simulator_before_publishing_unsigned_kit(self):
        import yaml
        job = yaml.load((ROOT/".github/workflows/ios-private.yml").read_text(),Loader=yaml.BaseLoader)["jobs"]["iphone"]
        steps = job["steps"]
        simulator = next(i for i,item in enumerate(steps) if "Check two native" in item.get("name",""))
        publish = next(i for i,item in enumerate(steps) if item.get("with",{}).get("name")=="sma-iphone-xcode-kit")
        self.assertGreater(publish,simulator)
        self.assertNotIn("if",steps[publish])  # Normal success gate; never publish failed native checks.
        self.assertTrue(any("CODE_SIGNING_ALLOWED=NO" in step.get("run","") for step in steps))
        self.assertNotIn("secrets.",(ROOT/".github/workflows/ios-private.yml").read_text())

    @skipUnless(importlib.util.find_spec("yaml"),"Install requirements-validation.txt for workflow checks")
    def test_source_cache_is_verified_before_saving_and_before_compilation(self):
        import yaml
        workflow=yaml.load((ROOT/".github/workflows/ios-private.yml").read_text(),Loader=yaml.BaseLoader)
        steps=workflow["jobs"]["iphone"]["steps"]
        verify=next(i for i,step in enumerate(steps) if "scripts.prepare_ios_sources" in step.get("run",""))
        save=next(i for i,step in enumerate(steps) if step.get("uses")=="actions/cache/save@v4")
        compile=next(i for i,step in enumerate(steps) if step.get("name")=="Compile Python, Kivy and the iPhone project")
        self.assertLess(verify,save)
        self.assertLess(save,compile)
        manifest=json.loads((ROOT/"ios/native-sources.json").read_text())["openssl"]
        for step in steps:
            if step.get("uses") in ("actions/cache/restore@v4","actions/cache/save@v4"):
                paths=step["with"]["path"].split()
                self.assertEqual({Path(path).name for path in paths},set(manifest["cache_files"]))
