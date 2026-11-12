"""Regression coverage for final APK signing and compiled manifest enforcement."""
import importlib.util
import io
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
import zipfile

from scripts.verify_android_apk import (PACKAGE, PERMISSIONS, fingerprint, parse_manifest_dump,
                                       verify_contents, verify_manifest, verify_signer)
from sma_analyzer.version import APP_VERSION


def node(tag, **attributes):
    return {"tag": tag, "attributes": attributes, "children": []}


def manifest():
    root = node("manifest", package=PACKAGE, **{"android:versionName": APP_VERSION})
    root["children"].append(node("uses-sdk", **{"android:targetSdkVersion": 35}))
    root["children"].extend(node("uses-permission", **{"android:name": name}) for name in PERMISSIONS)
    app = node("application", **{"android:" + name: False for name in (
        "debuggable", "allowBackup", "fullBackupContent", "usesCleartextTraffic")})
    launcher = node("activity", **{"android:name": "org.kivy.android.PythonActivity", "android:exported": True})
    intents = node("intent-filter")
    intents["children"] = [node("action", **{"android:name": "android.intent.action.MAIN"}),
                           node("category", **{"android:name": "android.intent.category.LAUNCHER"})]
    launcher["children"].append(intents)
    app["children"] = [launcher,
        node("service", **{"android:name": PACKAGE + ".ServiceSmaalerts", "android:exported": False}),
        node("service", **{"android:name": PACKAGE + ".SmaBackgroundService", "android:exported": False,
                           "android:process": ":sma_background_alerts"}),
        node("service", **{"android:name": "androidx.work.impl.background.systemjob.SystemJobService",
                           "android:exported": True, "android:permission": "android.permission.BIND_JOB_SERVICE"})]
    root["children"].append(app)
    return root, app


class AndroidApkPolicyTests(TestCase):
    def test_actual_apk_certificate_must_match_the_retained_key_not_only_a_valid_signature(self):
        expected = "92:3F:5D:E5:65:12:85:96:87:3E:31:97:08:E2:78:9D:91:40:48:F9"
        published = "Signer #1 certificate SHA-1 digest: 50aeb2c1d575265caa95f9294f5cdfbc32439150\n"
        with self.assertRaisesRegex(ValueError, "differs"):
            verify_signer(published, expected)
        proper = "Signer #1 certificate SHA-1 digest: " + fingerprint(expected).lower() + "\n"
        self.assertEqual(verify_signer(proper, expected), fingerprint(expected))

    def test_absent_or_additional_signers_are_rejected(self):
        signer = "Signer #1 certificate SHA-1 digest: " + "1" * 40 + "\n"
        for output in ("", signer + signer.replace("#1", "#2")):
            with self.assertRaises(ValueError):
                verify_signer(output, "1" * 40)
        with self.assertRaises(ValueError):
            fingerprint("not a fingerprint")

    def test_aapt_parser_preserves_compiled_booleans_and_attribute_ownership(self):
        output = '''N: android=http://schemas.android.com/apk/res/android
  E: manifest (line=2)
    A: package="org.thewongphoto.smaanalyzer" (Raw: "org.thewongphoto.smaanalyzer")
    E: application (line=30)
      A: android:debuggable(0x0101000f)=(type 0x12)0x0
      E: service (line=40)
        A: android:name(0x01010003)="Private" (Raw: "Private")
        A: android:exported(0x01010010)=(type 0x12)0x0
      E: receiver (line=45)
        A: android:name(0x01010003)="Protected" (Raw: "Protected")
        A: android:exported(0x01010010)=(type 0x12)0xffffffff
        A: android:permission(0x01010006)="android.permission.DUMP" (Raw: "android.permission.DUMP")
'''
        root = parse_manifest_dump(output)
        app = root["children"][0]
        self.assertIs(app["attributes"]["android:debuggable"], False)
        self.assertIs(app["children"][0]["attributes"]["android:exported"], False)
        self.assertIs(app["children"][1]["attributes"]["android:exported"], True)
        self.assertNotIn("android:permission", app["attributes"])

    def test_valid_release_retains_launcher_and_os_protected_workmanager_service(self):
        root, _ = manifest()
        result = verify_manifest(root)
        self.assertEqual(result["version"], APP_VERSION)
        self.assertEqual(set(result["permissions"]), PERMISSIONS)

    def test_absent_debug_flag_uses_androids_false_default_without_weakening_other_flags(self):
        root, app = manifest()
        del app["attributes"]["android:debuggable"]
        self.assertIs(verify_manifest(root)["application"]["debuggable"],False)
        del app["attributes"]["android:allowBackup"]
        with self.assertRaisesRegex(ValueError,"allowBackup"):
            verify_manifest(root)

    def test_debug_backup_or_cleartext_regressions_fail_the_release_gate(self):
        for attribute in ("debuggable", "allowBackup", "fullBackupContent", "usesCleartextTraffic"):
            for value in (True, None):
                root, app = manifest()
                app["attributes"]["android:" + attribute] = value
                with self.assertRaisesRegex(ValueError, attribute):
                    verify_manifest(root)

    def test_unused_foreground_and_sensitive_permissions_fail_the_release_gate(self):
        for name in ("FOREGROUND_SERVICE", "READ_SMS", "REQUEST_INSTALL_PACKAGES"):
            root, _ = manifest()
            root["children"].append(node("uses-permission", **{"android:name": "android.permission." + name}))
            with self.assertRaisesRegex(ValueError, "unexpected permissions"):
                verify_manifest(root)

    def test_exported_python_service_or_unprotected_job_service_is_rejected(self):
        for target, attribute, value in ((1, "android:exported", True),
                                          (2, "android:process", ":wrong"),
                                          (3, "android:permission", "")):
            root, app = manifest()
            app["children"][target]["attributes"][attribute] = value
            with self.assertRaises(ValueError):
                verify_manifest(root)

    def test_unknown_exported_components_are_rejected(self):
        root, app = manifest()
        app["children"].append(node("provider", **{"android:name": "Unexpected", "android:exported": True}))
        with self.assertRaisesRegex(ValueError, "exported component"):
            verify_manifest(root)

    def test_namespace_matching_receiver_permission_must_be_signature_protected(self):
        root, _ = manifest()
        name = PACKAGE + ".DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION"
        root["children"].append(node("uses-permission", **{"android:name": name}))
        with self.assertRaisesRegex(ValueError, "signature"):
            verify_manifest(root)
        root["children"].append(node("permission", **{"android:name": name, "android:protectionLevel": 2}))
        verify_manifest(root)

    def test_wrong_package_version_or_old_target_is_rejected(self):
        for attr, value in (("package", "wrong.package"), ("android:versionName", "0.0.0")):
            root, _ = manifest()
            root["attributes"][attr] = value
            with self.assertRaises(ValueError): verify_manifest(root)
        root, _ = manifest()
        root["children"][0]["attributes"]["android:targetSdkVersion"] = 22
        with self.assertRaisesRegex(ValueError, "target SDK"): verify_manifest(root)

    def test_private_databases_keys_and_unsafe_archive_paths_are_rejected(self):
        with TemporaryDirectory() as directory:
            apk = Path(directory) / "test.apk"
            for name in ("main.pyc", "saved_lines.sqlite3", "debug.keystore", "../outside", ".local/token.json"):
                payload = io.BytesIO()
                with tarfile.open(fileobj=payload, mode="w") as private:
                    member = tarfile.TarInfo(name)
                    member.size = 4
                    private.addfile(member, io.BytesIO(b"test"))
                with zipfile.ZipFile(apk, "w") as archive:
                    archive.writestr("assets/private.tar", payload.getvalue())
                if name == "main.pyc":
                    verify_contents(apk)
                else:
                    with self.assertRaises(ValueError): verify_contents(apk)

    @skipUnless(importlib.util.find_spec("yaml"), "Install requirements-validation.txt")
    def test_only_verified_signed_release_apks_are_uploaded_and_failures_keep_diagnostics(self):
        import yaml
        workflow = yaml.load((Path(__file__).parents[1] / ".github/workflows/android-debug.yml").read_text(),
                             Loader=yaml.BaseLoader)
        steps = workflow["jobs"]["apk"]["steps"]
        build = next(i for i, step in enumerate(steps) if "buildozer -v android release" in step.get("run", ""))
        self.assertIn('P4A_RELEASE_KEYSTORE="$HOME/.android/debug.keystore"', steps[build]["run"])
        verify = next(i for i, step in enumerate(steps) if "scripts.verify_android_apk" in step.get("run", ""))
        upload = next(i for i, step in enumerate(steps) if "bin/*.apk" in step.get("with", {}).get("path", ""))
        self.assertLess(build, verify)
        self.assertLess(verify, upload)
        self.assertEqual(steps[upload]["if"], "success()")
        diagnostic = next(step for step in steps if step.get("with", {}).get("name") == "sma-android-diagnostics")
        self.assertEqual(diagnostic["if"], "always()")
        self.assertNotIn("bin/", diagnostic["with"]["path"])
