# Verified mobile build sources

The 0.11.1 logs show HTTP 504 responses from GitHub's source-archive frontend for
Android's PyJNIus and iPhone's Kivy. Version 0.11.2 fetches those archives directly
from GitHub's official `codeload.github.com` server and verifies their SHA-256
before either toolchain uses them. No third-party mirror or TLS exception is used.

The [shared manifest](../scripts/native-archives.json) records the official
repository, ref, resolved commit, URL, checksum, size and exact recipe cache
filenames for each source:

| Source | Pinned ref | Platform |
| --- | --- | --- |
| Kivy | 2.3.1 | Android and iPhone |
| PyJNIus | 1.7.0 | Android |
| CPython | v3.14.2 | Android host and device |
| libffi | v3.4.2 | Android |
| SQLite | version-3.50.4 | Android |
| Pyobjus | 0c204ada4a5aa4f065ac65fc678c6cb35e4dcb81 | iPhone |

These are the existing recipes' versions. Resolve refs through the official Git
repository and compare zip comments/tar commit metadata when changing pins.
A checksum mismatch must stop the build; never update a checksum simply to
accept an unexpected download. GitHub release assets are not rewritten to Git
snapshots because generated source contents can differ.

OpenSSL's separate official commit pin and compatible legacy release checksum
remain in [ios/native-sources.json](../ios/native-sources.json). Its detailed
[provenance record](IOS_NATIVE_SOURCES.md) explains the original 0.11.0 failure.

## Android cache

`python -m scripts.prepare_android_sources` verifies canonical sources under
`.local/native-archives` and atomically copies them to the arm64 build's p4a
`packages/<recipe>/<original filename>` paths. It creates `.mark-<filename>`
only after verification. Without that marker, p4a deletes an archive and
downloads it again. A stale marker is removed before replacing a bad file.
The upstream recipe's own digest checks still run when it consumes the cache.

The workflow saves the verified source cache before SDK/native compilation,
so later compilation failures do not discard successful source downloads.
`android-native-sources.log` is included in the APK diagnostic artifact.

## iPhone cache and temporary probes

`python -m scripts.prepare_ios_sources .build-ios/toolchain/.cache` verifies the
host/device OpenSSL, Kivy and Pyobjus archives. `scripts.prepare_ios` performs
the same preflight for a local Mac build.

Kivy's `get_required_sdl_version()` normally downloads into a temporary directory
before its ordinary recipe starts. The process-local
[`scripts/ios_toolchain.py`](../scripts/ios_toolchain.py) wrapper intercepts the
official recipe download method and copies known verified archives even to those
temporary paths. Other GitHub source snapshots use the direct archive server;
release assets and other endpoints keep their original routes. Installed
third-party files are not modified.

All CLI subcommands use the wrapper, including pip/create, whose recipe discovery
can repeat the version probe. The workflow runs:

```sh
python -m scripts.check_ios_source_probe .build-ios/toolchain/.cache
```

This exercises the real upstream Kivy probe with networking disabled and checks
that the pinned source selects SDL2. Sources are saved before native compilation.
`ios-native-sources.log` and `ios-source-probe.log` accompany the build diagnostics.
The unsigned device build, signing-kit verification and two simulator launches
still gate publication of the iPhone kit.
