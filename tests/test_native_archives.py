import configparser
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase,skipUnless
from unittest.mock import Mock,patch
from urllib.error import HTTPError

from scripts.native_archives import (ROOT,direct_archive_url,install_ios_archive_transport,
                                      prepare_platform_sources,source_specs)
from scripts.source_fetch import ensure_verified_source


class NativeArchiveTests(TestCase):
    def setUp(self):
        temporary=TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.cache=self.root/"cache"
        self.cache.mkdir()
        self.payload=b"Controlled native source fixture"
        self.spec={"id":"fixture","version":"2.3.1","commit":"pinned-commit",
            "source_url":"https://github.com/kivy/kivy/archive/2.3.1.zip",
            "url":"https://codeload.github.com/kivy/kivy/zip/refs/tags/2.3.1",
            "filename":"kivy-2.3.1.zip","sha256":hashlib.sha256(self.payload).hexdigest(),
            "android_cache":["kivy/2.3.1.zip"],"ios_cache":["kivy-2.3.1.zip"]}
        (self.cache/self.spec["filename"]).write_bytes(self.payload)

    def test_source_archive_redirects_are_bypassed_without_renaming_the_recipe_file(self):
        for original,expected in (
            ("https://github.com/kivy/pyjnius/archive/1.7.0.zip","https://codeload.github.com/kivy/pyjnius/zip/1.7.0"),
            ("https://github.com/python/cpython/archive/refs/tags/v3.14.2.tar.gz","https://codeload.github.com/python/cpython/tar.gz/refs/tags/v3.14.2"),
            ("https://github.com/a/b/archive/commit.zip#sha256=abc","https://codeload.github.com/a/b/zip/commit#sha256=abc")):
            self.assertEqual(direct_archive_url(original),expected)

    def test_release_assets_other_hosts_and_signed_queries_keep_their_original_route(self):
        for url in ("https://github.com/libffi/libffi/releases/download/v3.4.8/libffi-3.4.8.tar.gz",
                    "https://example.org/a/archive/tag.zip", "https://github.com/a/b/archive/tag.zip?token=private",
                    "http://github.com/a/b/archive/tag.zip"):
            self.assertEqual(direct_archive_url(url),url)

    def test_android_verified_archive_has_the_completion_marker_p4a_requires(self):
        packages=self.root/"packages"
        with patch("scripts.source_fetch.urlopen",side_effect=AssertionError("No network needed")):
            self.assertEqual(prepare_platform_sources("android",packages,self.cache,[self.spec]),["fixture"])
        archive=packages/"kivy/2.3.1.zip"
        self.assertEqual(archive.read_bytes(),self.payload)
        self.assertIn(self.spec["sha256"],(archive.parent/".mark-2.3.1.zip").read_text())

    def test_failed_verification_removes_a_stale_android_marker_before_any_build(self):
        packages=self.root/"packages"
        archive=packages/"kivy/2.3.1.zip"
        archive.parent.mkdir(parents=True)
        archive.write_bytes(b"partial download")
        marker=archive.parent/".mark-2.3.1.zip"
        marker.write_text("old marker")
        (self.cache/self.spec["filename"]).unlink()
        with patch("scripts.source_fetch.urlopen",return_value=io.BytesIO(b"wrong bytes")):
            with self.assertRaisesRegex(RuntimeError,"checksum mismatch"):
                prepare_platform_sources("android",packages,self.cache,[self.spec])
        self.assertFalse(marker.exists())

    def test_ios_temporary_version_probe_gets_a_verified_copy_without_a_network_request(self):
        original=Mock(side_effect=AssertionError("The old GitHub frontend must not be contacted"))
        class Recipe:
            download_file=original
        restore=install_ios_archive_transport(Recipe,self.cache,[self.spec])
        try:
            with patch("scripts.source_fetch.urlopen",side_effect=AssertionError("No network")):
                Recipe().download_file(self.spec["source_url"],"temporary-kivy.zip",self.root/"probe")
            self.assertEqual((self.root/"probe/temporary-kivy.zip").read_bytes(),self.payload)
            original.assert_not_called()
        finally:
            restore()
        self.assertIs(Recipe.download_file,original)

    def test_unknown_archive_keeps_the_sdk_filename_and_its_own_checksum_handling(self):
        original=Mock()
        class Recipe:
            download_file=original
        restore=install_ios_archive_transport(Recipe,self.cache,[])
        try:
            recipe=Recipe()
            recipe.download_file("https://github.com/a/b/archive/tag.zip","tag.zip","/tmp")
            original.assert_called_once_with(recipe,"https://codeload.github.com/a/b/zip/tag","tag.zip","/tmp")
        finally:
            restore()

    def test_rate_limit_retry_after_is_not_ignored_by_a_fast_retry(self):
        spec=dict(self.spec,cache_files=["new.zip"])
        opener=Mock(side_effect=HTTPError(spec["url"],429,"Rate limit",{"Retry-After":"120"},None))
        wait=Mock()
        with self.assertRaisesRegex(RuntimeError,"Retry-After"):
            ensure_verified_source(self.root/"new",spec,opener,wait)
        opener.assert_called_once()
        wait.assert_not_called()

    def test_pins_cover_both_reported_failures_and_every_android_github_source_archive(self):
        from scripts.prepare_ios import TOOLCHAIN_REVISION
        specs={item["id"]:item for item in source_specs()}
        self.assertEqual(specs["kivy"]["version"],"2.3.1")
        self.assertEqual(specs["pyjnius"]["version"],"1.7.0")
        android={target for spec in specs.values() for target in spec["android_cache"]}
        self.assertEqual(android,{"kivy/2.3.1.zip","pyjnius/1.7.0.zip","hostpython3/v3.14.2.tar.gz",
            "python3/v3.14.2.tar.gz","libffi/v3.4.2.tar.gz","sqlite3/version-3.50.4.tar.gz"})
        manifest=json.loads((ROOT/"scripts/native-archives.json").read_text())
        config=configparser.ConfigParser();config.read(ROOT/"buildozer.spec")
        self.assertEqual(config["app"]["p4a.branch"],manifest["android_toolchain"])
        self.assertEqual(TOOLCHAIN_REVISION,manifest["ios_toolchain"])

    @skipUnless(importlib.util.find_spec("yaml"),"Install requirements-validation.txt for workflow checks")
    def test_android_verifies_and_saves_sources_before_native_compilation(self):
        import yaml
        workflow=yaml.load((ROOT/".github/workflows/android-debug.yml").read_text(),Loader=yaml.BaseLoader)
        steps=workflow["jobs"]["apk"]["steps"]
        verify=next(i for i,step in enumerate(steps) if "scripts.prepare_android_sources" in step.get("run",""))
        save=next(i for i,step in enumerate(steps) if step.get("uses")=="actions/cache/save@v4")
        compile=next(i for i,step in enumerate(steps) if "buildozer -v android debug" in step.get("run",""))
        self.assertLess(verify,save)
        self.assertLess(save,compile)
        config=configparser.ConfigParser();config.read(ROOT/"buildozer.spec")
        self.assertEqual(config["app"]["android.archs"],"arm64-v8a")
