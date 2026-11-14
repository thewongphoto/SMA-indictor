# Release history

The latest source version and requested Android build are **0.18.0** /
**apk-v0.18.0**. A tag or source commit does not prove native compilation passed.
Check the [Android workflow](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml)
for the run matching the desired tag and its downloadable artifact.

| Version | Changes retained in the current app |
| --- | --- |
| 0.18.0 | Fixes the Android tab divider after safe-area/keyboard moves; restores the original teal price line on both platforms. Brings native chart presentation to iPhone web: shared Manrope/logo assets, dollar headline prices, company identity, axes/legend, exact Python upward-crossing pluses, daily close/SMA touch inspection, native range/pinch rules, and visibility-aware overlays. Saved parameters and calculations are unchanged. |
| 0.17.0 | Tracks email additions, modifications and explicit removals from Android/web, with automatic source/version and an owner-only notification containing active/removed address summaries. Adds private Supabase registry/history, frozen email snapshots, retry/revision guards and Remove/Retry controls. Requires rerunning the email SQL for protocol 2. |
| 0.16.0 | Adds the optional full-screen email welcome and Settings editor on iPhone web/Android, with Vercel forwarding opt-in signups to the owner through Resend. Adds separate Supabase rate-limit/idempotency/count metadata, acceptance/error/retry handling and a beginner `/setup/email` guide. Signup stays hidden until configured. |
| 0.15.0 | Runs web SMA/backtests locally using the shared Python engine in Pyodide/NumPy, retains parameters in IndexedDB, adds backup import, and implements Supabase-scheduled Web Push with an owner setup page. Keeps legacy worker mode and native Android behaviour. |
| 0.14.3 | Owner corrections to the design: "+ Find SMA" is an outlined pill; the tab bar has its top divider; Home cards show larger company names, a $ price with drawn ▲/▼ change arrows, the design's "Hide lines"/"N saved lines" toggle, and each line's name in bold with its colour to the right, above "N signals / year"; the Charts status card text is larger. Prices use $ for every listing (US and SGX); chart captions still name the quote currency. |
| 0.14.2 | Completes the November design on Android, which 0.14.0 had only partly applied: Charts follows designs 02/2b (large price, plain-language status, range and signal chips, Find best SMA, and the new backtest card with horizon chips, buys/date summary, gain bars and the 500-sample statistic); Settings follows 04 (cards for notification types, background check, appearance, market data and legal); search follows 10/11 (teal Search, name-first results with Open/Analyse, recent securities, guided example card); Home pills and summary (01), empty Home (12), offline warning card (13), search error card (14), edit-line sheet (09), calculating overlay (07) and the first-open email screen (06, when signup is configured). The web backtest card matches 2b. Calculations, saved data and alert rules are unchanged. |
| 0.14.1 | Each saved line chooses its own signal types: Buy signal and both Impending buy signals can be switched per line in the Alerts tab on Android and iPhone web, under the existing master switches in Settings. Upgrades keep every type On, archive/restore keeps the choices, and lines with no type On make no scheduled requests. |
| 0.14.0 | Applies the November UI/UX handover to Android and a new iPhone web app: four tabs, cached watchlist status, frequency presets, editable saved lines, themes, readable backtests and cancel controls. Adds conditional opt-in signup, a private Python web worker, browser checks and deployment instructions. |
| 0.13.8 | Fixes APK certificate parsing for SDK Build Tools 37 while retaining single-signer and retained-key checks; retains public certificate diagnostics even when verification fails. |
| 0.13.7 | Corrects release lint by letting Gradle own debug mode. Native compilation passed, but the final-APK verifier rejected the new SDK certificate output format; no APK was uploaded. |
| 0.13.6 | Introduces explicit retained-key release signing and validates the final APK certificate; enforces non-debuggable/private/no-backup/HTTPS package policy, removes unused foreground-service declarations, and uploads APKs only after verification. Documents the unresolved Play Protect warning and older signing mismatch. Its initial build failed release lint and produced no verified APK; superseded by 0.13.7. |
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

## 0.14.0 UI/UX redesign

See the [handover](uiux-handover/README.md) and
[implementation record](uiux-handover/IMPLEMENTATION.md). Existing saved identities,
periods, colours, native alert rules, calendar-year calculations and APK signing
remain compatible. Web hosting, SMTP configuration and iPhone Web Push delivery
are separate from source/APK publication; no native iOS release is requested.

## 0.13.8 APK verification repair

The [0.13.7 run](https://github.com/thewongphoto/SMA-indictor/actions/runs/43195884927)
passed native compilation and release lint, then failed with `Final APK signer
differs from the retained signing identity`. SDK Build Tools 37 changed certificate
labels from `Signer #1 certificate SHA-1 digest:` to scheme-specific labels such
as `V2 Signer: certificate SHA-1 digest:` and `V3.0 Signer: certificate SHA-1 digest:`.
The verifier's old expression matched no certificate and incorrectly classified
that parsing failure as an identity mismatch. The failed run did not retain its
certificate output or APK, so it does not establish that APK's actual fingerprint.

The format change was reproduced with official SDK 35 and 37 against the same
0.13.5 APK, plus a disposable, locally signed v3 test fixture. Version 0.13.8
accepts both output formats, requires exactly one signer and one certificate,
and still rejects a certificate that differs from the retained key. Unknown
output now reports a parse error. Public `android-apk-signature.txt` evidence
is retained in diagnostics before policy checks. No signing key, package identity,
lint rule or APK policy has been changed to resolve this parser defect.

## Package security since 0.13.6

Inspection of the distributed 0.13.5 APK confirmed valid APK v2 signing, but its
actual certificate did not match the retained keystore reported by CI. The
0.13.3 APK had another certificate. The previous debug build relied on default
Gradle signing without explicitly binding the retained key. Release signing now
specifies that key, and CI checks the final APK certificate after compilation.

The merged manifest now requires debugging, backups and cleartext traffic to be
disabled. The unused foreground-service permissions/component are removed;
scheduled checks retain WorkManager and their private bound Python service.
Only verified APKs are uploaded, with diagnostics retained separately.

The first release attempt (0.13.6) failed `HardcodedDebugMode` lint because the
manifest hook wrote `debuggable=false` explicitly. Version 0.13.7 removes the
generated attribute so Gradle controls it by variant. The final APK must still
be effectively non-debuggable; Android defaults a missing flag to false. Release
lint stays enabled, with no baseline or suppression for this error.

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
