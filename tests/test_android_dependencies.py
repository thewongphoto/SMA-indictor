"""Exercise the CI dependency installer without sudo or network access."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless


ROOT = Path(__file__).resolve().parents[1]


class AndroidDependencyInstallerTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.calls = self.root / "calls.jsonl"
        (self.bin / "sudo").write_text('#!/bin/sh\nexec "$@"\n')
        (self.bin / "apt-get").write_text(
            f"#!{sys.executable}\n" + '''import json, os, pathlib, sys
args = sys.argv[1:]
options = dict(value.split("=", 1) for index, value in enumerate(args)
               if index and args[index-1] == "-o")
source = pathlib.Path(options["Dir::Etc::sourcelist"])
lists = pathlib.Path(options["Dir::State::lists"])
assert lists.is_dir()
record = {"args": args, "sources": source.read_text(), "directory": str(source.parent),
          "list_files": sorted(str(p.relative_to(lists)) for p in lists.rglob("*")),
          "noninteractive": os.environ.get("DEBIAN_FRONTEND")}
with open(os.environ["SMA_APT_TEST_CALLS"], "a") as stream:
    stream.write(json.dumps(record) + "\\n")
operation = "update" if args[-1] == "update" else "install"
if operation == os.environ.get("SMA_APT_TEST_FAIL"):
    print("Controlled repository download failure", file=sys.stderr)
    sys.exit(100)
''')
        for script in self.bin.iterdir():
            script.chmod(0o755)

    def run_installer(self, fail=""):
        environment = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                           TMPDIR=str(self.root), SMA_APT_TEST_CALLS=str(self.calls),
                           SMA_APT_TEST_FAIL=fail)
        result = subprocess.run(["bash", str(ROOT / "scripts/install_android_deps.sh")],
                                env=environment, text=True, capture_output=True)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        for call in calls:
            self.assertFalse(Path(call["directory"]).exists(), "Temporary apt state must be removed")
        return result, calls

    def test_update_and_install_use_fresh_signed_official_https_repositories(self):
        result, calls = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["args"][-1], "update")
        self.assertIn("install", calls[1]["args"])
        self.assertEqual(calls[0]["directory"], calls[1]["directory"])
        expected = [
            ("archive.ubuntu.com", "jammy"), ("archive.ubuntu.com", "jammy-updates"),
            ("archive.ubuntu.com", "jammy-backports"), ("security.ubuntu.com", "jammy-security")]
        for call in calls:
            self.assertEqual(call["sources"].splitlines(), [
                "deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] "
                f"https://{host}/ubuntu {suite} main restricted universe multiverse"
                for host, suite in expected])
            self.assertEqual(call["noninteractive"], "noninteractive")
            for option in ("Dir::Etc::sourceparts=-", "APT::Update::Error-Mode=any",
                           "Acquire::Retries=3", "Acquire::http::Timeout=20",
                           "Acquire::https::Timeout=20"):
                self.assertIn(option, call["args"])
        self.assertEqual(calls[0]["list_files"], ["partial"])
        for package in ("libtinfo5", "cmake", "xvfb", "libegl1", "libmtdev1", "xclip"):
            self.assertIn(package, calls[1]["args"])

    def test_failed_update_stops_before_install_and_preserves_the_apt_exit_status(self):
        result, calls = self.run_installer("update")
        self.assertEqual(result.returncode, 100)
        self.assertEqual(len(calls), 1)
        self.assertIn("Controlled repository download failure", result.stderr)

    def test_failed_package_download_is_not_reported_as_success(self):
        result, calls = self.run_installer("install")
        self.assertEqual(result.returncode, 100)
        self.assertEqual(len(calls), 2)

    @skipUnless(importlib.util.find_spec("yaml"), "Install requirements-validation.txt")
    def test_workflow_captures_setup_failures_and_limits_the_dependency_step(self):
        import yaml
        workflow = yaml.load((ROOT / ".github/workflows/android-debug.yml").read_text(),
                             Loader=yaml.BaseLoader)
        steps = workflow["jobs"]["apk"]["steps"]
        dependency_index = next(index for index, step in enumerate(steps)
                                if "scripts/install_android_deps.sh" in step.get("run", ""))
        dependency = steps[dependency_index]
        self.assertEqual(dependency["timeout-minutes"], "15")
        self.assertIn("set -o pipefail", dependency["run"])
        self.assertIn("tee artifacts/android-deps.log", dependency["run"])
        self.assertIn("pip install", steps[dependency_index + 1]["run"])
        upload = next(step for step in steps if step.get("uses") == "actions/upload-artifact@v4")
        self.assertEqual(upload["if"], "always()")
        self.assertIn("artifacts/android-deps.log", upload["with"]["path"])
