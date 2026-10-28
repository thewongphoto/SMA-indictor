# Android/Gmail validation status

## Completed checks

- **67 Python unit tests passed**, zero failures/skips. Coverage includes the
  existing math/storage/policy and new Gmail MIME/HTTPS, sender configuration,
  TLS, access-token expiry, safe errors, no automatic retry on uncertain sends,
  independent email/phone dispatch and deduplication.
- **26 running Kivy UI groups passed**, including fake Google consent/HTTP for
  Connect Gmail, explicit test send, preview isolation and disconnect. All prior
  screen navigation, table, sheet, chart, persistence and sizing checks pass.
- Android API fakes exercise permission granted/denied, notification channel,
  disabled app/channel settings, monochrome icon fallback, stable IDs and tap
  PendingIntent. These checks do not substitute for Android execution.
- `pip check` passed for the desktop environment. Python sources compile.
- The configured Buildozer/p4a tags exist upstream. Their source handling for
  added Java/resources was inspected. The build uses p4a v2026.05.09 and its
  recommended NDK 28c, with Buildozer 1.6.0.

## APK build attempt: blocked, no APK produced

Build tooling was installed in a separate `.venv-android`. The cloud's default
home directory is read-only, so a local-only probe redirected Buildozer's global
cache to the writable workspace without changing HOME. With the build environment
activated, the actual debug-build attempt reached the tool checks and stopped at:

```text
Search for Java compiler (javac)
Java compiler (javac) not found, please install it.
```

The Android SDK/NDK are absent; Google-hosted downloads are blocked in this
workspace. There is no attached Android phone/emulator. Java bridge compilation,
APK installation, OS permission prompts, real Google consent, TLS on-device and
real email delivery have **not** been verified. No account has been authorized
and no real email or phone notification has been sent from this session.

A manual GitHub Actions build workflow is provided. It has **not** been run here;
the available GitHub CLI authentication cannot dispatch it. Git repository pushes
work, so the workflow and guide are available for the user to run in GitHub.

Start with [the Android APK guide](ANDROID_APK_GUIDE.md). A successful workflow
run is the next native-compilation checkpoint, followed by phone and Gmail tests.
