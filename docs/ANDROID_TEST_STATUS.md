# Validation and build status

Current source: **0.14.1**. The matching Android build tag is **apk-v0.14.1**.
Native build completion must be checked in
[GitHub Actions](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml).
A published tag or uploaded diagnostic ZIP alone does not prove an APK exists.

Release 0.14.1 adds per-line signal types. Host validation ran **351 tests, all
passing**, plus the extended four-tab regression (per-line
Alerts switches, persistence and disabled state), every Android UI gate and the
web worker/browser checks including per-line toggles after reload. One
`smoke_ui` run failed a fixed-frame expand/collapse wait while other heavy jobs
shared the CPU; it passed when re-run alone and also passes unchanged on 0.14.0.

The 0.14.0 unit run completed **342 tests: 340 passed and two optional checks
skipped**. The production web build and browser workflow passed against the
isolated Python fixture worker. Native UI gates include the new four-tab/theme
regressions as well as all retained Android checks. Final run results and
artifacts are linked by the release workflow. Vercel deployment and physical
iPhone/Android testing are separate from these host fixtures.

Release 0.13.8 host validation previously ran **337 tests: 335 passed and two optional
checks skipped** (NumPy and desktop yfinance). All **eight Android UI gates**
and the additional desktop Yahoo fixture passed: **152 UI checks** in total.
All **133 local link targets in 30 Markdown documents** passed.

Sixteen APK-policy tests cover actual signer comparison, SDK 35/37 output
formats, compiled manifest parsing, release flags, permissions, exported components, packaged private data
and verified-only distribution. Running the official SDK against the old 0.13.5
APK reproduced the certificate mismatch and policy failures. The new final-APK
gate must pass after native compilation before a binary can be uploaded.

The 0.13.7 native build and release lint passed, but its certificate parser
did not recognize SDK 37's scheme-specific labels and stopped APK upload.
The format incompatibility was reproduced using official SDK 35 and 37 on the
same APK. Version 0.13.8 retains strict identity checks and saves public
certificate diagnostics; [details](CHANGELOG.md#0138-apk-verification-repair).

The dependency installer was also verified in a clean Ubuntu 22.04 container
for 0.13.5; its repository and timeout policy is unchanged. Its regression tests
cover isolation, bounded setup, failure propagation and retained logs.
The [0.13.5 repair record](CHANGELOG.md#0135-build-repair) describes the original
runner DNS failure, which stopped 0.13.4 before tests or native compilation.
The [package audit](ANDROID_PACKAGE_SECURITY.md) records the 0.13.5 signing
defect and OnePlus 13R/Android 16 warning. **Google Play Protect clearance remains
unverified**; local/CI package checks do not establish Google's classification
or physical-device behaviour.

| Evidence | What it establishes |
| --- | --- |
| Unit checks | Arithmetic, persistence/migrations, transport fixtures, scheduling rules, adapters and packaging metadata. |
| Running Kivy UI checks | Real widget/gesture/layout behaviour with temporary fixture data; includes offline startup and the mobile transport path. |
| Successful Actions native job | APK compilation and retained signing identity for that exact commit. |
| Physical Android testing | Real provider/network/device/permission/OS behaviour for that installed artifact. |

Host validation does not invent a physical-phone result or claim the GitHub native
job has already completed. Earlier videos/logs relate to their recorded builds.

The iPhone Vercel/PWA route is documented but not implemented/deployed in this
repository. Retained native iOS fixtures are compatibility checks, not evidence
that a new iPhone release or browser port exists.

[Release checklist](ANDROID_RELEASE_CHECKLIST.md) ·
[Data/request-log testing](YAHOO_ANDROID_TESTING.md) ·
[Background notification testing](ANDROID_DAILY_NOTIFICATIONS.md)
