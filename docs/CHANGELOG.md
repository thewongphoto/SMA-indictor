# Release history

The latest source version and requested Android build are **0.13.6** /
**apk-v0.13.6**. A tag or source commit does not prove native compilation passed.
Check the [Android workflow](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml)
for the run matching the desired tag and its downloadable artifact.

| Version | Changes retained in the current app |
| --- | --- |
| 0.13.6 | Uses explicit retained-key release signing and validates the final APK certificate; enforces non-debuggable/private/no-backup/HTTPS package policy, removes unused foreground-service declarations, and uploads APKs only after verification. Documents the unresolved Play Protect warning and older signing mismatch. |
| 0.13.5 | Repairs Android dependency setup after the runner's Ubuntu mirror DNS failure; uses signed official HTTPS repositories, fresh package indexes, bounded retries, strict update failures and retained setup logs. Fixes links to the renamed documentation index. |
| 0.13.4 | Repository/documentation cleanup; removes unused Gmail transport, native auth bridge and Google sign-in dependency; preserves old saved-data fields and blocks retired delivery channels. |
| 0.13.3 | Fixes offline chart startup without currency metadata and a CI scrolling-test timing assumption. |
| 0.13.2 | Visible-range currency/% comparison, correct upward price-crossing logo, launch branding and repeating calculation animation; portable PNG validation. |
| 0.13.1 | Live annualization and yearly horizons use 365 calendar days; initial app icon and iPhone verifier correction. |
| 0.13.0 | Bounded Android background-service startup, diagnostic background test and start-of-trading reminders. |
| 0.12.0 | 3M/6M/9M ranges; VOO guide defaults to 4/year and Max with selectable horizons. |
| 0.11.x | Centred palette, retained native iPhone experiment and verified source-download caches. Native iPhone releases are now paused. |
| 0.10.x | Merged search/preferences, names, colours, animated navigation, daily phone checks and offline issuer logos. |
| 0.8–0.9.x | Real private market data, persistent caches, request logs and mobile chart refinements. |
| 0.4–0.7.x | Phone-only UI, grouped saved lines, library-first flow and early offline search/design reviews. |
| Earlier | Initial offline analysis and retired email prototype. |

## 0.13.6 package security

Inspection of the distributed 0.13.5 APK confirmed valid APK v2 signing, but its
actual certificate did not match the retained keystore reported by CI. The
0.13.3 APK had another certificate. The previous debug build relied on default
Gradle signing without explicitly binding the retained key. Release signing now
specifies that key, and CI checks the final APK certificate after compilation.

The merged manifest now requires debugging, backups and cleartext traffic to be
disabled. The unused foreground-service permissions/component are removed;
scheduled checks retain WorkManager and their private bound Python service.
Only verified APKs are uploaded, with diagnostics retained separately.

The [package audit](ANDROID_PACKAGE_SECURITY.md) records the exact evidence and
the OnePlus 13R/Android 16 Play Protect warning. Its detection rationale is still
unknown; these package fixes are not proof of Google clearance. The reporting
user has no installed app/data to migrate. Existing installations with a different
signer still require a data-preserving migration rather than routine replacement.

## 0.13.5 build repair

The [0.13.4 run](https://github.com/thewongphoto/SMA-indictor/actions/runs/43057259805)
failed during Linux dependency installation: APT repeatedly reported
`Temporary failure resolving 'azure.archive.ubuntu.com'` and exited with code
100. Python dependency installation, regression tests and APK compilation never
ran. The runner's package access failure stopped the build before application
compilation.

The Android job now invokes `scripts/install_android_deps.sh` against the
official Ubuntu Jammy HTTPS repositories, using the runner's Ubuntu archive
keyring and fresh temporary indexes. Failed index downloads stop setup instead
of falling back to stale metadata. Requests have bounded retries/timeouts;
the Linux dependency step has a 15-minute limit. Both successful and failed
dependency output is retained in `artifacts/android-deps.log`.

The documentation index remains `docs/1.Directory.md`; references to its old
name were updated so the next build's documentation gate can pass. Application
data, package/signing identity and calculation behaviour are unchanged. Native
iOS builds remain paused. The new tag requests a fresh build; its successful
native job and APK artifact must still be verified separately.

Older per-version documents, screen proposals and the development diary have
been removed from the current tree. Their exact content remains in previous
commits/tags. For example, the
[pre-cleanup tree](https://github.com/thewongphoto/SMA-indictor/tree/3059e6b)
contains the earlier records. Released tags have not been deleted or rewritten.

The Vercel/PWA document is the current iPhone deployment plan. It does not mean
a browser frontend, synchronization backend or production URL already exists.
