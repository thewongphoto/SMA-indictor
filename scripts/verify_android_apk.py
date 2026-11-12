"""Verify the distributed APK, including its actual signer and merged manifest.

This is a package policy check, not a malware verdict or Play Protect clearance.
The Android SDK supplies aapt and apksigner; no APK code is executed.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import zipfile

from sma_analyzer.version import APP_VERSION

PACKAGE = "org.thewongphoto.smaanalyzer"
PERMISSIONS = {"android.permission." + name for name in (
    "INTERNET", "POST_NOTIFICATIONS", "WAKE_LOCK", "RECEIVE_BOOT_COMPLETED", "ACCESS_NETWORK_STATE")}
PROTECTED_EXPORTS = {
    "androidx.work.impl.background.systemjob.SystemJobService": "android.permission.BIND_JOB_SERVICE",
    "androidx.work.impl.diagnostics.DiagnosticsReceiver": "android.permission.DUMP",
    "androidx.profileinstaller.ProfileInstallReceiver": "android.permission.DUMP",
}


def fingerprint(value):
    normalized = value.replace(":", "").strip().upper()
    if not re.fullmatch(r"[0-9A-F]{40}", normalized):
        raise ValueError("Expected a SHA-1 signing certificate fingerprint")
    return normalized


def verify_signer(output, expected):
    actual = re.findall(r"^Signer #\d+ certificate SHA-1 digest:\s*(\S+)", output, re.MULTILINE)
    if len(actual) != 1 or fingerprint(actual[0]) != fingerprint(expected):
        raise ValueError("Final APK signer differs from the retained signing identity")
    return fingerprint(actual[0])


def parse_manifest_dump(output):
    """Read aapt's compiled XML tree, preserving component/attribute ownership."""
    stack = []
    root = None
    for line in output.splitlines():
        element = re.match(r"(\s*)E: ([\w.-]+)(?:\s|$)", line)
        if element:
            depth = len(element[1])
            node = {"tag": element[2], "attributes": {}, "children": []}
            while stack and stack[-1][0] >= depth:
                stack.pop()
            if stack:
                stack[-1][1]["children"].append(node)
            else:
                if root is not None:
                    raise ValueError("Multiple manifest roots")
                root = node
            stack.append((depth, node))
            continue
        attribute = re.match(r"\s*A: ([\w:]+)(?:\(0x[0-9a-fA-F]+\))?=(.*)", line)
        if attribute and stack:
            value = attribute[2]
            if value.startswith('"'):
                value = json.JSONDecoder().raw_decode(value)[0]
            else:
                typed = re.fullmatch(r"\(type 0x([0-9a-fA-F]+)\)0x([0-9a-fA-F]+)", value)
                if typed:
                    value = bool(int(typed[2], 16)) if int(typed[1], 16) == 0x12 else int(typed[2], 16)
            stack[-1][1]["attributes"][attribute[1]] = value
    if root is None or root["tag"] != "manifest":
        raise ValueError("No compiled Android manifest found")
    return root


def verify_manifest(root, version=APP_VERSION):
    attributes = root["attributes"]
    if attributes.get("package") != PACKAGE or attributes.get("android:versionName") != version:
        raise ValueError("APK package/version differs from the selected release")
    sdk = next(node["attributes"] for node in root["children"] if node["tag"] == "uses-sdk")
    if sdk.get("android:targetSdkVersion", 0) < 35:
        raise ValueError("APK target SDK is older than the supported build policy")
    permissions = {node["attributes"].get("android:name") for node in root["children"]
                   if node["tag"].startswith("uses-permission")}
    internal = PACKAGE + ".DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION"
    if permissions - PERMISSIONS - {internal}:
        raise ValueError("APK declares unexpected permissions: " + str(sorted(permissions - PERMISSIONS - {internal})))
    if not PERMISSIONS <= permissions:
        raise ValueError("APK is missing required network/notification/job permissions")
    if internal in permissions:
        definition = next((node for node in root["children"] if node["tag"] == "permission"
                           and node["attributes"].get("android:name") == internal), None)
        if definition is None or definition["attributes"].get("android:protectionLevel") != 2:
            raise ValueError("Internal receiver permission must require the matching signature")
    application = next(node for node in root["children"] if node["tag"] == "application")
    for name in ("debuggable", "allowBackup", "fullBackupContent", "usesCleartextTraffic"):
        if application["attributes"].get("android:" + name) is not False:
            raise ValueError("Release policy requires android:" + name + "=false")
    components = []
    private_services = set()
    for node in application["children"]:
        if node["tag"] not in {"activity", "activity-alias", "service", "receiver", "provider"}:
            continue
        attrs = node["attributes"]
        name = attrs.get("android:name")
        exported = attrs.get("android:exported", any(child["tag"] == "intent-filter" for child in node["children"]))
        if exported:
            if name == "org.kivy.android.PythonActivity" and node["tag"] == "activity":
                intents = {item["attributes"].get("android:name") for child in node["children"]
                           if child["tag"] == "intent-filter" for item in child["children"]}
                if not {"android.intent.action.MAIN", "android.intent.category.LAUNCHER"} <= intents:
                    raise ValueError("Exported Python activity must be the launcher")
            elif name not in PROTECTED_EXPORTS or attrs.get("android:permission") != PROTECTED_EXPORTS[name]:
                raise ValueError("Unexpected/unprotected exported component: " + str(name))
        if name in {PACKAGE + ".ServiceSmaalerts", PACKAGE + ".SmaBackgroundService"}:
            if attrs.get("android:exported") is not False:
                raise ValueError("Python services must be explicitly private")
            private_services.add(name)
            if name.endswith(".SmaBackgroundService") and attrs.get("android:process") != ":sma_background_alerts":
                raise ValueError("Bound Python service must keep its dedicated process")
        components.append({"name": name, "exported": exported, "permission": attrs.get("android:permission")})
    if len(private_services) != 2:
        raise ValueError("Missing private Python service declarations")
    return {"package": PACKAGE, "version": version, "target_sdk": sdk["android:targetSdkVersion"],
            "permissions": sorted(permissions), "components": components,
            "application": {name: application["attributes"]["android:" + name] for name in
                            ("debuggable", "allowBackup", "fullBackupContent", "usesCleartextTraffic")}}


def verify_contents(path):
    with Path(path).open("rb") as stream:
        if stream.read(4) != b"PK\x03\x04":
            raise ValueError("APK must have a standard ZIP header")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise ValueError("APK has duplicate entries or invalid ZIP checksums")
        if any(PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts for name in names):
            raise ValueError("Unsafe APK ZIP path")
        with tarfile.open(fileobj=io.BytesIO(archive.read("assets/private.tar"))) as private:
            for member in private:
                parts = PurePosixPath(member.name)
                if parts.is_absolute() or ".." in parts.parts or member.issym() or member.islnk():
                    raise ValueError("Unsafe path/link in packaged Python application")
                if any(part in {".git", ".local", ".venv", ".venv-android", "artifacts"} for part in parts.parts):
                    raise ValueError("Development/private state was included in APK")
                if parts.suffix in {".sqlite3", ".keystore", ".jks", ".p12", ".p8"}:
                    raise ValueError("Private data or signing files were included in APK")


def build_tools_directory():
    roots = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT"),
             str(Path.home() / ".buildozer/android/platform/android-sdk"),
             str(Path.cwd() / ".buildozer/android/platform/android-sdk")]
    for root in roots:
        if not root:
            continue
        candidates = [p for p in (Path(root) / "build-tools").glob("*")
                      if re.fullmatch(r"\d+\.\d+\.\d+", p.name)
                      and (p / "aapt").is_file() and (p / "apksigner").is_file()]
        if candidates:
            return max(candidates, key=lambda p: tuple(map(int, p.name.split("."))))
    raise ValueError("Android SDK aapt/apksigner are required to verify the final APK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path)
    parser.add_argument("--build-tools", type=Path)
    parser.add_argument("--signing-info", type=Path, default=Path("artifacts/android-signing-info.txt"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/android-apk-verification.json"))
    args = parser.parse_args()
    paths = [args.apk] if args.apk else list(Path("bin").glob("*.apk"))
    if len(paths) != 1:
        raise ValueError("Expected exactly one APK from this build")
    apk = paths[0]
    tools = args.build_tools or build_tools_directory()
    expected = re.search(r"^SHA1: (\S+)$", args.signing_info.read_text(), re.MULTILINE)
    if expected is None:
        raise ValueError("Missing retained signing identity report")
    signature = subprocess.run([str(tools / "apksigner"), "verify", "--verbose", "--print-certs", str(apk)],
                               check=True, capture_output=True, text=True).stdout
    actual = verify_signer(signature, expected[1])
    dump = subprocess.run([str(tools / "aapt"), "dump", "xmltree", str(apk), "AndroidManifest.xml"],
                          check=True, capture_output=True, text=True).stdout
    report = verify_manifest(parse_manifest_dump(dump))
    verify_contents(apk)
    with apk.open("rb") as stream:
        report.update(sha256=hashlib.file_digest(stream, "sha256").hexdigest(), bytes=apk.stat().st_size,
                      signer_sha1=actual, signature_verified=True, file=str(apk), play_protect_clearance="not_verified")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print("Final APK signature, release flags, permissions, components and contents verified.")


if __name__ == "__main__":
    main()
