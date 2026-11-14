import importlib.util
import json
from pathlib import Path
import plistlib
import shutil
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts.make_iphone_kit import make_kit
from scripts.prepare_ios import (ROOT, configure_info, configure_project, stage_app, APP_VERSION,
                                 BUNDLE_ID, background_task_identifiers, project_reference_path)
from scripts.verify_iphone_kit import verify


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
                           ("sma_analyzer/assets/logos/brand.png","png"),("sma_analyzer/assets/logos/CREDITS.txt","credits"),
                           ("sma_analyzer/assets/chart-style.json",'{"price":{}}'),
                           ("sma_analyzer/assets/private.json","must not ship")):
            (source/name).write_text(value)
        destination = self.directory/"stage"
        destination.mkdir()
        (destination/"old-token.json").write_text("must not ship")
        stage_app(destination,source)
        names = {str(file.relative_to(destination)) for file in destination.rglob("*") if file.is_file()}
        self.assertEqual(names,{"main.py","sma_analyzer/app.py","sma_analyzer/assets/logos/brand.png","sma_analyzer/assets/logos/CREDITS.txt","sma_analyzer/assets/chart-style.json"})
        with self.assertRaises(ValueError):
            stage_app(source,source)

    def test_info_allows_supported_free_capabilities_and_expands_the_selected_bundle_id(self):
        info = configure_info({"CFBundleExecutable":"smaanalyzer"})
        self.assertEqual(info["CFBundleShortVersionString"],APP_VERSION)
        self.assertEqual(info["UILaunchStoryboardName"],"Launch Screen")
        self.assertEqual(info["UIBackgroundModes"],["fetch"])
        self.assertEqual(info["CFBundleIdentifier"],"$(PRODUCT_BUNDLE_IDENTIFIER)")
        self.assertEqual(info["BGTaskSchedulerPermittedIdentifiers"],[
            "$(PRODUCT_BUNDLE_IDENTIFIER).refresh.US","$(PRODUCT_BUNDLE_IDENTIFIER).refresh.SG",
            "$(PRODUCT_BUNDLE_IDENTIFIER).refresh.US_START","$(PRODUCT_BUNDLE_IDENTIFIER).refresh.SG_START"])
        self.assertEqual(info["UISupportedInterfaceOrientations"],["UIInterfaceOrientationPortrait"])
        self.assertNotIn("NSAppTransportSecurity",info)

    def fake_app(self, platform="iPhoneOS"):
        app = self.directory/"app.app"
        app.mkdir()
        (app/"Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable":"smaanalyzer","CFBundleSupportedPlatforms":[platform],
            "CFBundleIcons":{"CFBundlePrimaryIcon":{"CFBundleIconName":"AppIcon","CFBundleIconFiles":["AppIcon60x60"]}}}))
        (app/"smaanalyzer").write_bytes(b"unsigned compiled fixture; not an installable binary")
        (app/"smaanalyzer").chmod(0o755)
        (app/"embedded.mobileprovision").write_text("private profile must be excluded")
        (app/"YourApp").mkdir()
        (app/"YourApp/main.pyc").write_bytes(b"fixture")
        (app/"Assets.car").write_bytes(b"compiled icon resource fixture; not a device asset catalog")
        return app

    def test_kit_preserves_compiled_payload_without_shipping_signing_credentials(self):
        app=self.fake_app()
        original_icons=plistlib.loads((app/"Info.plist").read_bytes())["CFBundleIcons"]
        kit = make_kit(app,self.directory/"kit")
        self.assertTrue((kit/"UnsignedApp.app/YourApp/main.pyc").is_file())
        self.assertFalse((kit/"UnsignedApp.app/embedded.mobileprovision").exists())
        self.assertFalse(json.loads((kit/"BUILD_INFO.json").read_text())["signed"])
        self.assertEqual(plistlib.loads((kit/"Info.plist").read_bytes())["CFBundleIdentifier"],"$(PRODUCT_BUNDLE_IDENTIFIER)")
        scheme = ET.parse(kit/"SMA-iPhone.xcodeproj/xcshareddata/xcschemes/smaanalyzer.xcscheme")
        self.assertEqual(scheme.find(".//BuildableReference").attrib["ReferencedContainer"],"container:SMA-iPhone.xcodeproj")
        self.assertIn("--exclude /Info.plist",(kit/"copy-payload.sh").read_text())
        self.assertIn("--exclude /embedded.mobileprovision",(kit/"copy-payload.sh").read_text())
        self.assertEqual(plistlib.loads((kit/"Info.plist").read_bytes())["CFBundleIcons"],original_icons)
        self.assertIn("Assets.car",json.loads((kit/"BUILD_INFO.json").read_text())["icon_resources_sha256"])

    def test_signing_kit_verifier_accepts_all_four_jobs_and_rejects_missing_or_extra_ids(self):
        app=self.fake_app()
        kit=make_kit(app,self.directory/"kit")
        info=configure_info(plistlib.loads((app/"Info.plist").read_bytes()))
        info["CFBundleIdentifier"]=BUNDLE_ID
        # Exact four-entry processed plist seen in the failed native 0.13.0 build.
        info["BGTaskSchedulerPermittedIdentifiers"]=[BUNDLE_ID+".refresh.US",BUNDLE_ID+".refresh.SG",
                                                   BUNDLE_ID+".refresh.US_START",BUNDLE_ID+".refresh.SG_START"]
        (app/"Info.plist").write_bytes(plistlib.dumps(info))
        verify(app,kit/"BUILD_INFO.json")  # Regression: 0.13.0 rejected the two opening identifiers.
        for invalid in (background_task_identifiers(BUNDLE_ID)[:2],
                        background_task_identifiers(BUNDLE_ID)+[BUNDLE_ID+".refresh.UNKNOWN"]):
            info["BGTaskSchedulerPermittedIdentifiers"]=invalid
            (app/"Info.plist").write_bytes(plistlib.dumps(info))
            with self.assertRaisesRegex(ValueError,"Background task identifiers"):
                verify(app,kit/"BUILD_INFO.json")

    def test_signing_kit_verifier_rejects_a_dropped_or_modified_icon(self):
        app=self.fake_app()
        kit=make_kit(app,self.directory/"kit")
        info=configure_info(plistlib.loads((app/"Info.plist").read_bytes()))
        info["CFBundleIdentifier"]=BUNDLE_ID
        info["BGTaskSchedulerPermittedIdentifiers"]=background_task_identifiers(BUNDLE_ID)
        (app/"Info.plist").write_bytes(plistlib.dumps(info))
        (app/"Assets.car").write_bytes(b"wrong payload")
        with self.assertRaisesRegex(ValueError,"icon resources"):
            verify(app,kit/"BUILD_INFO.json")
        (app/"Assets.car").unlink()
        with self.assertRaisesRegex(ValueError,"missing its AppIcon resources"):
            verify(app,kit/"BUILD_INFO.json")

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
        catalog=base/"smaanalyzer/Images.xcassets"
        catalog.mkdir(parents=True)
        # A second catalog with the same basename must not hide the app catalog.
        unrelated=base/"legacy/Images.xcassets"
        unrelated.mkdir(parents=True)
        project=XcodeProject.load(str(base/"smaanalyzer.xcodeproj/project.pbxproj"))
        project.add_file(str(unrelated))
        project.save()
        with patch("scripts.prepare_ios.install_app_icons",return_value=catalog) as icons:
            project = XcodeProject.load(str(configure_project(base)/"project.pbxproj"))
        icons.assert_called_once_with(base,ROOT/"sma_analyzer/assets/app-icon.png")
        bridge = next(item for item in project.objects.get_objects_in_section("PBXFileReference") if item.path.endswith("SMAIOSBridge.m"))
        buildfile = next(item for item in project.objects.get_objects_in_section("PBXBuildFile") if item.fileRef==bridge.get_id())
        self.assertEqual(buildfile.settings["COMPILER_FLAGS"].strip(),"-fobjc-arc")
        for config in project.objects.get_objects_in_section("XCBuildConfiguration"):
            self.assertEqual(config.buildSettings["CODE_SIGN_STYLE"],"Automatic")
            self.assertEqual(config.buildSettings["IPHONEOS_DEPLOYMENT_TARGET"],"15.0")
            self.assertEqual(config.buildSettings["ASSETCATALOG_COMPILER_APPICON_NAME"],"AppIcon")
        icons=[item for item in project.objects.get_objects_in_section("PBXFileReference")
               if project_reference_path(project,item,base)==catalog.resolve()]
        self.assertEqual(len(icons),1)
        resource_ids={project.get_object(build).fileRef
                      for phase in project.objects.get_objects_in_section("PBXResourcesBuildPhase")
                      for build in phase.files}
        self.assertIn(icons[0].get_id(),resource_ids)
        self.assertIn("IOS_IS_WINDOWED=True",(base/"main.m").read_text())
        self.assertIn("KIVY_NO_ARGS=1",(base/"main.m").read_text())
        self.assertEqual((base/"icon.png").read_bytes(),(ROOT/"sma_analyzer/assets/app-icon.png").read_bytes())
        launch=ET.parse(base/"Storyboards/Launch Screen.storyboard")
        self.assertEqual(launch.find(".//imageView").attrib["image"],"icon.png")
        self.assertEqual({item.attrib.get("firstAttribute") for item in launch.findall(".//constraint")},
                         {"width","height","centerX","centerY"})
        for resource in (base/"icon.png",base/"Storyboards/Launch Screen.storyboard"):
            reference=next(item for item in project.objects.get_objects_in_section("PBXFileReference")
                           if project_reference_path(project,item,base)==resource.resolve())
            self.assertIn(reference.get_id(),resource_ids)

    @skipUnless(importlib.util.find_spec("pbxproj"),"Install requirements-validation.txt for Xcode project checks")
    def test_official_group_catalog_reference_resolves_to_the_generated_icon_directory(self):
        from pbxproj import XcodeProject
        base=self.directory/"smaanalyzer-ios"
        shutil.copytree(ROOT/"ios/signing-template",base)
        project=XcodeProject.load(str(base/"SMA-iPhone.xcodeproj/project.pbxproj"))
        catalog=base/"smaanalyzer/Images.xcassets"
        catalog.mkdir(parents=True)
        project.add_file(str(catalog))
        reference=next(item for item in project.objects.get_objects_in_section("PBXFileReference")
                       if str(getattr(item,"path","")).endswith("Images.xcassets"))
        # These are the exact path/sourceTree fields in the pinned kivy-ios template.
        reference.path="smaanalyzer/Images.xcassets"
        reference.sourceTree="<group>"
        self.assertEqual(project_reference_path(project,reference,base),catalog.resolve())
        # Also support a real subgroup directory instead of its display name.
        group=project.add_group("Icon resources",path="smaanalyzer")
        for parent in project.objects.get_objects_in_section("PBXGroup"):
            if reference.get_id() in parent.children:
                parent.remove_child(reference)
        group.add_child(reference)
        reference.path="Images.xcassets"
        self.assertEqual(project_reference_path(project,reference,base),catalog.resolve())

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
        sources=json.loads((ROOT/"scripts/native-archives.json").read_text())["sources"]
        expected=set(manifest["cache_files"])|{name for source in sources for name in source["ios_cache"]}
        for step in steps:
            if step.get("uses") in ("actions/cache/restore@v4","actions/cache/save@v4"):
                paths=step["with"]["path"].split()
                self.assertEqual({Path(path).name for path in paths},expected)

    def test_every_ios_cli_command_uses_the_archive_transport_wrapper(self):
        from scripts import prepare_ios
        with patch.object(prepare_ios,"ROOT",self.directory),patch.object(prepare_ios,"stage_app"),\
             patch.object(prepare_ios,"prepare_ios_sources"),patch.object(prepare_ios.shutil,"which",return_value="toolchain"),\
             patch.object(prepare_ios.sys,"platform","darwin"),patch.object(prepare_ios.sys,"argv",["prepare_ios"]),\
             patch.object(prepare_ios,"configure_project",return_value=self.directory/"app.xcodeproj"),\
             patch.object(prepare_ios,"run") as run:
            prepare_ios.main()
        commands=[call.args[0] for call in run.call_args_list]
        self.assertEqual([command[2] for command in commands],["build","pip","create"])
        self.assertTrue(all(command[1]==self.directory/"scripts/ios_toolchain.py" for command in commands))
