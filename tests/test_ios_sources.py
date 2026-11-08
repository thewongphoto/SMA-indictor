import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock
from urllib.error import HTTPError

from scripts.prepare_ios_sources import ROOT,ensure_native_sources,sha256


class NativeSourceTests(TestCase):
    def setUp(self):
        directory=TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cache=Path(directory.name)
        self.payload=b"fixture for the pinned source archive"
        self.legacy=b"fixture for the original release archive"
        self.source={"version":"1.1.1w","commit":"pinned-commit",
            "url":"https://codeload.github.com/openssl/openssl/tar.gz/pinned-commit",
            "sha256":hashlib.sha256(self.payload).hexdigest(),
            "released_archive_sha256":hashlib.sha256(self.legacy).hexdigest(),
            "cache_files":["hostopenssl-openssl-1.1.1w.tar.gz","openssl-openssl-1.1.1w.tar.gz"]}

    def test_transient_504_retries_and_installs_both_verified_recipe_archives(self):
        opener=Mock(side_effect=[HTTPError(self.source["url"],504,"Gateway Time-out",{},None),io.BytesIO(self.payload)])
        wait=Mock()
        result=ensure_native_sources(self.cache,self.source,opener,wait)
        self.assertEqual(opener.call_count,2)
        self.assertTrue(opener.call_args.args[0].full_url.startswith("https://"))
        wait.assert_called_once_with(1)
        self.assertEqual(set(result["cache"].values()),{self.source["sha256"]})
        self.assertTrue(all((self.cache/name).read_bytes()==self.payload for name in self.source["cache_files"]))

    def test_valid_cached_release_is_reused_without_network_or_changing_its_bytes(self):
        target=self.cache/self.source["cache_files"][0]
        target.write_bytes(self.legacy)
        opener=Mock()
        result=ensure_native_sources(self.cache,self.source,opener)
        opener.assert_not_called()
        self.assertEqual(set(result["cache"].values()),{self.source["released_archive_sha256"]})
        self.assertEqual(target.read_bytes(),self.legacy)

    def test_each_valid_archive_keeps_its_existing_extraction_identity(self):
        for name,payload in zip(self.source["cache_files"],(self.legacy,self.payload)):
            (self.cache/name).write_bytes(payload)
        opener=Mock()
        result=ensure_native_sources(self.cache,self.source,opener)
        opener.assert_not_called()
        self.assertEqual(len(set(result["cache"].values())),2)

    def test_partial_archive_from_a_failed_download_is_replaced(self):
        target=self.cache/self.source["cache_files"][0]
        target.write_bytes(b"truncated")
        opener=Mock(return_value=io.BytesIO(self.payload))
        ensure_native_sources(self.cache,self.source,opener)
        self.assertEqual(sha256(target),self.source["sha256"])

    def test_checksum_mismatch_never_installs_the_download(self):
        opener=Mock(return_value=io.BytesIO(b"unexpected source bytes"))
        with self.assertRaisesRegex(RuntimeError,"checksum mismatch"):
            ensure_native_sources(self.cache,self.source,opener)
        self.assertFalse(any(self.cache.iterdir()))

    def test_persistent_gateway_error_is_bounded_and_leaves_no_partial_archive(self):
        opener=Mock(side_effect=HTTPError(self.source["url"],504,"Gateway Time-out",{},None))
        wait=Mock()
        with self.assertRaisesRegex(RuntimeError,"three HTTPS attempts"):
            ensure_native_sources(self.cache,self.source,opener,wait)
        self.assertEqual(opener.call_count,3)
        self.assertEqual(wait.call_count,2)
        self.assertFalse(any(self.cache.iterdir()))

    def test_non_transient_http_error_and_plain_http_do_not_retry(self):
        opener=Mock(side_effect=HTTPError(self.source["url"],404,"Not found",{},None))
        wait=Mock()
        with self.assertRaises(HTTPError):
            ensure_native_sources(self.cache,self.source,opener,wait)
        wait.assert_not_called()
        with self.assertRaisesRegex(RuntimeError,"HTTPS"):
            ensure_native_sources(self.cache,dict(self.source,url="http://example.com/source"),opener,wait)
        self.assertEqual(opener.call_count,1)

    def test_manifest_pins_the_official_tag_commit_and_both_native_recipe_cache_names(self):
        manifest=json.loads((ROOT/"ios/native-sources.json").read_text())["openssl"]
        self.assertEqual(manifest["url"],"https://codeload.github.com/openssl/openssl/tar.gz/"+manifest["commit"])
        self.assertEqual(len(manifest["commit"]),40)
        self.assertEqual(len(manifest["sha256"]),64)
        self.assertEqual(set(manifest["cache_files"]),
            {f"{recipe}-openssl-{manifest['version']}.tar.gz" for recipe in ("hostopenssl","openssl")})
