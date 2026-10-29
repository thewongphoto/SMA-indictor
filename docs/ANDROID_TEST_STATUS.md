# Android/Gmail validation status

## Android device feedback and 0.2.1 corrections

The user installed the preceding APK and reported on **29 October 2026
(Singapore)** that **Test Android phone notification works**. That is a physical
phone success reported by the user, rather than an emulator/cloud claim.
Back navigation, email/EOD editing, saved-menu discovery and status-bar overlap
were reported failing on that prior build. Gmail real sending remains unconfirmed.

Version 0.2.1 implements:

- A page stack and native Back handler: editor/overlay first, then prior page,
  exit only on Parameters. Fixed Back controls retain the same behavior.
- Native Android surface/system-bar/cutout/IME measurements. The whole app and
  sheet fit the usable area; already-inset surfaces are not padded twice. Input
  focus survives touch replay and viewport reflow, with focused-field scrolling.
  Desktop window sizing/minimums are no longer applied to Android.
- A clickable Saved SMAs icon **and label**, explicitly positioned bottom sheet,
  and all-counter/scenario saved rows on Parameters. View opens the exact saved
  counter, scenario, period and target without optimization. Results keeps Hide.
- Durable signing-secret restore, expected-SHA-1 validation and no silent key
  regeneration. One-time user repository setup is required to retain the cached
  key: [signing guide](ANDROID_SIGNING.md).
- A [saved device release checklist](ANDROID_RELEASE_CHECKLIST.md) and unit/UI
  regression steps in the APK workflow.

The new Java window helper **compiles against real Android API 35**. SQLite
persistence passes a subprocess test that skips graceful cleanup with
`os._exit(0)`. A real `keytool` round trip retains the same fingerprint through
base64-secret restore, and absence of the key fails closed. Desktop focus/typing
checks inject keyboard/inset measurements; **the actual phone keyboard and all
0.2.1 changes still need retesting on a new APK**. This workspace has no phone,
emulator or complete native packaging toolchain. No email was sent here.

## GitHub build failure and fix — 29 October 2026

The supplied log is from [workflow run 40702420820](https://github.com/thewongphoto/SMA-indictor/actions/runs/40702420820),
building commit `3c81aef`. It reached `:compileDebugJavaWithJavac` and failed
with three `cannot find symbol` errors in `GmailAuthBridge.java`, all referring
to `RevokeAccessRequest`.

**Root cause:** `buildozer.spec` pinned Google `play-services-auth` to **21.3.0**,
but the bridge uses `RevokeAccessRequest` and `AuthorizationClient.revokeAccess`,
which are available in **21.4.0**. Inspection of the actual Google Maven AARs
confirmed that 21.3.0 contains neither API and 21.4.0 contains both. The fix pins
**21.4.0**, preserving account-specific, send-scope revocation on Disconnect.
No change to the Java bridge, notification behavior, prices or SMA math is needed.

The earlier `No matching distribution found` messages for Pyjnius, `android`
and Kivy are unsuccessful **prebuilt-wheel probes**. The same log subsequently
records successful source builds and installation of all three Android wheels.
The Clang configuration probe errors and deprecation warnings also did not stop
the build. They are not additional causes of this failure.

### Targeted native regression check

The unchanged Java bridge was compiled with the real Android **API 35**
`android.jar`, Google `play-services-auth` AAR classes and its published
`play-services-base`, `play-services-basement` and `play-services-tasks`
dependencies. This check used Java 8 source/target options and the installed
JDK 21 compiler module, invoked with `java com.sun.tools.javac.Main` because
this workspace has no `javac` executable.

| Actual compile check | Result |
| --- | --- |
| Original `play-services-auth:21.3.0` | Reproduced the same three compiler errors |
| Configured replacement `play-services-auth:21.4.0` | Passed, exit code 0 |

Libraries came from Google's Maven repository and official Android SDK
`platform-35_r02.zip`. No fake Google classes were used for this compile check.
No third-party binaries, account credentials or uploaded full logs are committed.

For that fix, the targeted check verifies the bridge's
Java API compatibility; it does not perform Gradle packaging or device execution.
Start a **new Run workflow on main** after the fix is pushed. **Re-run failed
jobs** on the original run uses the old commit and would retain the old dependency.

## Completed checks

- **75 Python unit tests passed**, zero failures/skips. Coverage includes the
  existing math/storage/policy and new Gmail MIME/HTTPS, sender configuration,
  TLS, access-token expiry, safe errors, no automatic retry on uncertain sends,
  independent email/phone dispatch and deduplication.
- **30 running Kivy UI groups passed**, including four new Android regression
  groups and fake Google consent/HTTP for
  Connect Gmail, explicit test send, preview isolation and disconnect. All prior
  screen navigation, table, sheet, chart, persistence and sizing checks pass.
- The four focused Android UI groups also pass at density 2 in a 440×920 dp
  viewport. Keyboard/system bars are injected measurements, not a real IME.
- Android API fakes exercise permission granted/denied, notification channel,
  disabled app/channel settings, monochrome icon fallback, stable IDs and tap
  PendingIntent. These checks do not substitute for Android execution.
- `pip check` passed for the desktop environment. Python sources compile.
- The configured Buildozer/p4a tags exist upstream. Their source handling for
  added Java/resources was inspected. The build uses p4a v2026.05.09 and its
  recommended NDK 28c, with Buildozer 1.6.0.

## Original local APK build attempt: blocked, no APK produced

Build tooling was installed in a separate `.venv-android`. The cloud's default
home directory is read-only, so a local-only probe redirected Buildozer's global
cache to the writable workspace without changing HOME. With the build environment
activated, the actual debug-build attempt reached the tool checks and stopped at:

```text
Search for Java compiler (javac)
Java compiler (javac) not found, please install it.
```

At that initial attempt the Android SDK/NDK were absent and Google downloads
were blocked. This follow-up could download the SDK platform's `android.jar`
and Google Maven libraries for the targeted compilation above. A full configured
SDK/NDK toolchain and attached Android phone/emulator are still unavailable.
APK installation and generic phone notifications were subsequently exercised
by the user. OS prompts, real Google consent, TLS on-device and real email
delivery have **not** been independently verified here. No account has been
authorized and no real email or phone notification has been sent here.

A manual GitHub Actions workflow is provided. The user ran it and supplied the
failure log analyzed above, then tested a later APK. The 0.2.1 source updates
need a fresh complete build and the saved device checklist.
Git repository pushes work, but the available GitHub CLI authentication cannot
dispatch a new workflow. Use the workflow's **Run workflow** button on **main**.

Start with [the Android APK guide](ANDROID_APK_GUIDE.md). A successful workflow
run is the next native-compilation checkpoint, followed by phone and Gmail tests.
