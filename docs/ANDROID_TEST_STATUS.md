# Validation and build status

Current source: **0.13.4**. The matching Android build tag is **apk-v0.13.4**.
Native build completion must be checked in
[GitHub Actions](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml).
A published tag or uploaded diagnostic ZIP alone does not prove an APK exists.

Current host validation passes **317 unit checks** (two optional NumPy checks
skipped), all **eight running UI gates**, and all **120 local link targets in
29 Markdown documents**. The lower count than 0.13.3 reflects removal of tests
for deleted Gmail/spinner code and new retired-channel suppression coverage.
[0.13.4 release note](RELEASE_0_13_4.md).

| Evidence | What it establishes |
| --- | --- |
| Unit checks | Arithmetic, persistence/migrations, transport fixtures, scheduling rules, adapters and packaging metadata. |
| Running Kivy UI checks | Real widget/gesture/layout behaviour with temporary fixture data; includes offline startup and the mobile transport path. |
| Successful Actions native job | APK compilation and retained signing identity for that exact commit. |
| Physical Android testing | Real provider/network/device/permission/OS behaviour for that installed artifact. |

This cleanup does not invent a physical-phone result or claim the GitHub native
job has already completed. Earlier videos/logs relate to their recorded builds.

The iPhone Vercel/PWA route is documented but not implemented/deployed in this
repository. Retained native iOS fixtures are compatibility checks, not evidence
that a new iPhone release or browser port exists.

[Release checklist](ANDROID_RELEASE_CHECKLIST.md) ·
[Data/request-log testing](YAHOO_ANDROID_TESTING.md) ·
[Background notification testing](ANDROID_DAILY_NOTIFICATIONS.md)
