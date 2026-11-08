# 0.11.2 — Android and iPhone source-download corrections

Both uploaded 0.11.1 logs pass the previously failing checks. They stop at later
source downloads, before APK packaging or iPhone compilation:

| Build | First failing download | Error |
| --- | --- | --- |
| Android | PyJNIus 1.7.0 through `github.com/kivy/pyjnius/archive/1.7.0.zip` | HTTP 504 |
| iPhone | Kivy 2.3.1 through `github.com/kivy/kivy/archive/2.3.1.zip` | HTTP 504 |

The iPhone failure is in the toolchain's temporary SDL-version probe. That probe
uses its own temporary archive rather than the ordinary recipe download cache.
Fixing OpenSSL alone did not cover it.

## Changes

- Fetch the pinned GitHub source archives directly from the official
  `codeload.github.com` server, verify SHA-256, then populate the exact cache
  filenames expected by each toolchain. Versions and native sources are unchanged.
- Android prefetches Kivy, PyJNIus, CPython, libffi and SQLite. It creates p4a's
  completion markers only for verified files and saves sources before compiling.
- iPhone prefetches Kivy/Pyobjus in addition to OpenSSL. Every official toolchain
  invocation—build, pip and create—uses a process-local transport wrapper, so the
  temporary Kivy probe can copy the verified archive without a network call.
- The iPhone workflow runs that real upstream probe with networking disabled
  before compiling. Both workflows retain source verification logs in artifacts.

The centred palette, data/cache behavior and signing identities are retained.
No changes to GitHub secrets or the user's device settings are needed.
See [source pins, verification and cache rules](MOBILE_NATIVE_SOURCES.md).

## Validation and builds

All six pinned source archives were downloaded and their embedded commit metadata
matched against the official Git repositories. The actual upstream Android
`Recipe.download()` accepted all six recipe cache entries with downloads disabled.
The actual upstream iPhone Kivy version probe returned SDL2 with networking
disabled. Both clean Python 3.11 build environments passed the 276-test suite
(one desktop-only check skipped). Unit regressions cover checksum failure, partial/stale caches, retries,
legacy OpenSSL cache compatibility and routing all iPhone CLI subcommands.

Use **apk-v0.11.2** and **ios-v0.11.2**. Old tags retain their old code.
The native GitHub workflows still determine whether an APK/Xcode kit is ready;
source and fixture validation alone do not establish a completed native build.
