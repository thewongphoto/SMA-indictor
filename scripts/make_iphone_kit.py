"""Package an unsigned device app with a small Personal Team Xcode project."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil

from .prepare_ios import ROOT, APP_VERSION, BUNDLE_ID, configure_info, scheme_xml


def make_kit(app, destination):
    app, destination = Path(app), Path(destination)
    info = plistlib.loads((app / "Info.plist").read_bytes())
    if info.get("CFBundleExecutable") != "smaanalyzer" or not (app / "smaanalyzer").is_file():
        raise ValueError("Expected the compiled smaanalyzer device app.")
    if info.get("CFBundleSupportedPlatforms") != ["iPhoneOS"]:
        raise ValueError("The signing kit must contain an iPhone device binary, not a simulator app.")
    if destination.exists():
        raise ValueError("Use a new kit output directory; existing files are preserved.")
    shutil.copytree(ROOT / "ios/signing-template", destination)
    shutil.copytree(app, destination / "UnsignedApp.app", ignore=shutil.ignore_patterns("_CodeSignature", "embedded.mobileprovision"))
    (destination / "Info.plist").write_bytes(plistlib.dumps(configure_info(info)))
    scheme = destination / "SMA-iPhone.xcodeproj/xcshareddata/xcschemes/smaanalyzer.xcscheme"
    scheme.parent.mkdir(parents=True, exist_ok=True)
    scheme.write_text(scheme_xml("999999999999999999999999", "SMA-iPhone"))
    digest = hashlib.sha256((app / "smaanalyzer").read_bytes()).hexdigest()
    (destination / "BUILD_INFO.json").write_text(json.dumps({"version":APP_VERSION, "bundle_id":BUNDLE_ID,
        "executable_sha256":digest, "platform":"iPhoneOS arm64", "signed":False},indent=2))
    shutil.copy2(ROOT / "docs/PRIVATE_IPHONE_INSTALLATION.md", destination / "START_HERE.md")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(make_kit(args.app, args.destination))
