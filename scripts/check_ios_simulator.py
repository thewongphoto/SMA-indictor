"""Install a QA-only simulator app and require two fresh successful launches."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import subprocess
import time
import uuid


def run(*args, **kwargs):
    return subprocess.check_output([str(arg) for arg in args], text=True, **kwargs).strip()


def main(app, artifacts):
    artifacts.mkdir(parents=True, exist_ok=True)
    inventory = json.loads(run("xcrun", "simctl", "list", "devices", "available", "--json"))
    candidate = next((runtime, device) for runtime, devices in inventory["devices"].items()
                     if ".iOS-" in runtime for device in devices if "iPhone" in device["name"])
    runtime, reference = candidate
    device = run("xcrun", "simctl", "create", "SMA private CI check", reference["deviceTypeIdentifier"], runtime)
    bundle = plistlib.loads((app / "Info.plist").read_bytes())["CFBundleIdentifier"]
    try:
        run("xcrun", "simctl", "boot", device)
        run("xcrun", "simctl", "bootstatus", device, "-b")
        run("xcrun", "simctl", "install", device, app)
        container = Path(run("xcrun", "simctl", "get_app_container", device, bundle, "data"))
        for phase in (1,2):
            launch = uuid.uuid4().hex
            env = dict(os.environ, SIMCTL_CHILD_SMA_IOS_CHECK_ID=launch, SIMCTL_CHILD_SMA_IOS_CHECK_PHASE=str(phase))
            args = ["-NSDocumentRevisionsDebugMode","YES"] if phase==2 else []
            run("xcrun", "simctl", "launch", device, bundle, *args, env=env)
            deadline = time.monotonic()+60
            while time.monotonic() < deadline:
                files = list(container.rglob("ios-smoke-result.json"))
                result = json.loads(files[0].read_text()) if files else {}
                if result.get("launch_id") == launch:
                    (artifacts / f"launch-{phase}.json").write_text(json.dumps(result, indent=2))
                    if not result["passed"]:
                        raise RuntimeError(result["error"])
                    break
                time.sleep(.25)
            else:
                raise RuntimeError("Simulator did not confirm startup in 60 seconds.")
            # A deliberate fresh process must reread persisted SQLite state.
            subprocess.run(["xcrun","simctl","terminate",device,bundle],check=False)
        print("Two native iOS Simulator launches passed; physical iPhone/signing remain separate tests.")
    finally:
        subprocess.run(["xcrun","simctl","spawn",device,"log","show","--last","5m","--style","compact",
                        "--predicate",'process == "smaanalyzer"'], stdout=(artifacts / "simulator.log").open("w"),check=False)
        subprocess.run(["xcrun","simctl","shutdown",device],check=False)
        subprocess.run(["xcrun","simctl","delete",device],check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts/ios-simulator"))
    args = parser.parse_args()
    main(args.app, args.artifacts)
