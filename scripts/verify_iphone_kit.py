"""Check that Xcode installed the real payload and expanded the signing identity."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib


def verify(app, metadata):
    info = plistlib.loads((app/"Info.plist").read_bytes())
    expected = json.loads(metadata.read_text())
    actual = hashlib.sha256((app/"smaanalyzer").read_bytes()).hexdigest()
    if actual != expected["executable_sha256"]:
        raise ValueError("The Xcode kit did not copy the compiled Kivy executable.")
    identifier = info["CFBundleIdentifier"]
    if "$" in identifier or identifier != expected["bundle_id"]:
        raise ValueError("Xcode did not expand the selected bundle identifier.")
    if info["BGTaskSchedulerPermittedIdentifiers"] != [f"{identifier}.refresh.US",f"{identifier}.refresh.SG"]:
        raise ValueError("Background task identifiers do not match the signed app.")
    if not (app/"YourApp/main.pyc").is_file():
        raise ValueError("The compiled Python entry point is missing.")
    print("Xcode kit contains the compiled Kivy app with matching task identifiers; Apple signing remains local.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app",type=Path)
    parser.add_argument("metadata",type=Path)
    args = parser.parse_args()
    verify(args.app,args.metadata)
