# Retained native iOS source provenance

Native iOS releases are paused. This record and the referenced fixtures remain
for the previous native experiment; they do not configure the future Vercel
web app. Follow [the current iPhone guide](PRIVATE_IPHONE_INSTALLATION.md) for that route.

Version 0.11.2 also verifies/caches Kivy and Pyobjus and routes the toolchain's
temporary Kivy version probe through that cache. See
[the shared mobile source policy](MOBILE_NATIVE_SOURCES.md) for those pins and
the Android archive-download correction. The OpenSSL provenance below is retained.

The first iPhone workflow stopped while downloading
`http://www.openssl.org/source/openssl-1.1.1w.tar.gz`. Its redirect chain returned
HTTP 504 on all five attempts. No native compilation or signing had started.
The official GitHub release-asset endpoint also returned 504 during diagnosis.

The build now fetches the same **OpenSSL 1.1.1w** version as an immutable source
snapshot from OpenSSL's official GitHub repository:

- Tag: [OpenSSL_1_1_1w](https://github.com/openssl/openssl/tree/OpenSSL_1_1_1w)
- Commit: [`e04bd3433fd84e1861bf258ea37928d9845e6a86`](https://github.com/openssl/openssl/commit/e04bd3433fd84e1861bf258ea37928d9845e6a86)
- HTTPS archive: [official commit snapshot](https://codeload.github.com/openssl/openssl/tar.gz/e04bd3433fd84e1861bf258ea37928d9845e6a86)
- Snapshot SHA-256: `23c52cc22a7455b7fb260efa0804f4584ebbe08b66da231e22afbb026ea67b7c`

The release tag was resolved through the official Git repository. All **3,104**
source entries in the downloaded snapshot were compared with an archive made
from that Git commit: no files, contents, executable flags or symlink targets
differed. The version header identifies OpenSSL 1.1.1w, 11 September 2023.

The original released tarball has a different archive format/checksum:
`cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8`.
It remains an accepted existing cache entry. Its published checksum is recorded
in [Conan Center's OpenSSL source metadata](https://github.com/conan-io/conan-center-index/blob/master/recipes/openssl/1.x.x/conandata.yml).
Valid legacy archives are kept unchanged, preserving their recorded extraction
roots in partial local toolchain builds.

`scripts.prepare_ios_sources` validates both cached OpenSSL archives before reuse. It
downloads over verified HTTPS, retries transient network failures with bounded
backoff, checks the expected snapshot SHA-256 and installs files atomically into
the `hostopenssl` and `openssl` recipe caches. A checksum mismatch stops the
build; it never installs unverified bytes. Failed transfers leave no usable
partial download. Existing invalid/truncated archives are replaced.

The GitHub workflow saves the verified source cache before compiling libraries,
so a later native-build failure does not discard that download on a rerun.
Compiled-library cache keys also include the source manifest and Xcode version.
The ordinary Mac launcher performs the same preflight automatically.

Pins live in [ios/native-sources.json](../ios/native-sources.json). When changing
them, verify the official release/commit and archive contents first. Do not
replace expected checksums solely to accept an unexpected download.
