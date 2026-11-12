# Validation and build status

Current source: **0.13.5**. The matching Android build tag is **apk-v0.13.5**.
Native build completion must be checked in
[GitHub Actions](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml).
A published tag or uploaded diagnostic ZIP alone does not prove an APK exists.

Release 0.13.5 host validation ran **321 tests: 319 passed and two optional
checks skipped** (NumPy and desktop yfinance). All **eight Android UI gates**
and the additional desktop Yahoo fixture run passed: **152 UI checks** in
total. All **120 local link targets in 29 Markdown documents** passed.

The dependency installer also completed in a clean Ubuntu 22.04 container
with verified official HTTPS repositories. Four new regression tests cover
repository isolation, bounded setup, failure propagation and retained logs.
The [0.13.5 repair record](CHANGELOG.md#0135-build-repair) describes the original
runner DNS failure, which stopped 0.13.4 before tests or native compilation.

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
