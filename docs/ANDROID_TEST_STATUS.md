# Android validation status

## 0.6.0 — company identity and saved SMA enclosures

Parameters shows company logo/name in Selected security. Both saved libraries
show logo/name/ticker, reserve the ticker, and shorten names only at whole-word
boundaries. Expanded companies and their SMAs share separate rounded teal
enclosures. The recently unsaved archive uses smaller logos and company names.
Narrow phones stack parameter controls so names remain readable.

Validation: **100 unit tests** and **46 full running-widget UI groups** passed.
The three new groups cover 320/440/960dp identity layouts, word truncation,
reserved tickers, both group enclosures, synchronized accordions, View, archive
logo sizes and exact restoration. Current screenshots were inspected; syntax
and diff-whitespace checks pass. Shared Android widgets are exercised on cloud
desktop, not a physical phone. The `apk-v0.6.0` tag triggers the existing APK
workflow with the original signing identity. Actions API access is forbidden
in this session, so build completion is not established by these checks.

See [identity UI details](SECURITY_IDENTITY_UI.md).

## 0.5.0 — submit-only security-search preview

Search supports partial ticker/company names with packaged logos or initials,
exchange-qualified identities, Enter/Submit and explicit history selection.
Both requests run off the UI thread; duplicate pending submits and stale results
are suppressed. Search/history failures preserve the current analysis. The same
UI is used on desktop and Android, including keyboard-safe editing. Twelve Data
is not connected: the 12-security catalogue and all histories are local/simulated.
See SECURITY_SEARCH.md for exact behavior and validation commands.

Validation: **100 unit tests** and **43 full running-widget UI groups** passed.
The full run includes search request counts, actual logo-row taps, stale/failing
responses, keyboard geometry and a residual-scroll regression after navigation
and resizing. Packaged logos, dependency compatibility and Android packaging
configuration were checked. Live Twelve Data and physical-device execution are
not claimed.


## 0.4.0 — phone-only application

Email/Gmail UI and the application authorization/sending paths are removed.
Stored legacy email flags are ignored during preview and delivery. Phone settings,
permission handling and deduplication remain. The full UI runner now verifies
that email controls are absent on both saved libraries and Settings, including
a store migrated from email-enabled preferences, and that email-only alerts
passed directly to the application delivery boundary are ignored.

The APK workflow accepts `apk-v*` tag pushes as well as manual dispatch. The
signing identity is preserved. Older Gmail sections below are historical.

Current checks passed: **93 unit tests** and **38 running Kivy UI groups**,
including phone-only controls, legacy-email suppression, notification permission
denial/recovery, saved security accordions and the revised backtests. No new
physical-device result or completed APK build is claimed by these checks.

## 0.3.0 — current cloud validation

The user reports that the preceding Android fixes pass on their phone. This
version adds the saved-library, chart-inspection/pinch and investment changes.
These new changes have not yet been installed or verified on a physical phone.

- Full standard-library suite: **85 passed**, zero failures/skips. The three
  subsequently added Python/native callback lifecycle tests and the ending-value
  percentage-difference test also pass (**89 passing tests across those runs**).
- Full real-widget smoke: **33 groups passed**, zero failures. Exercises the
  ending values, b/c percentage differences versus a and period/custom validation; cursor date/EOD/SMA accuracy;
  single-finger drag without zoom; two-finger spread/contract and finger lift;
  preserved quick views; SGX/US interleaved saved lines across scenarios; the
  existing settings, Gmail mocks, notification previews and portrait layouts.
- After the final saved-title wrapping adjustment, the focused UI run passed
  all **5 groups**, including complete library discovery from every saved view.
- Modified Gmail Java bridge compiles against official Google auth 21.4.0,
  auth-base 18.0.10, base/basement 18.5.0 and tasks 18.2.0. This targeted compile
  uses the Android SDK API stub JAR from Maven; it is not a full APK build.
- A local JVM harness with real Google ApiException/Status classes exercises
  seven status-code branches plus unknown errors: pending callbacks clear and
  exception messages are not exposed. TextUtils.isEmpty is a JVM shim for the
  Android stub; no actual consent or Google account is involved in this check.
- Inspected exported EOD tooltip and full results screenshots: investment
  captions/values align right, dates say simulated, and full crossing details
  remain reachable separately.

Gmail's old message is insufficient to diagnose the phone's underlying problem:
the old bridge treated every non-OK Android result as cancellation. The new
bridge reads the returned Intent even with RESULT_CANCELED and shows numeric
Google failure codes, with separate handling for missing result data and Play
services availability. A new APK and real consent/send test are still required;
no cloud test establishes that the user's OAuth configuration is correct.
Build source version is **0.3.0**. No full APK was built or workflow launched in
this change. Keep the existing signing identity for the next build.

## Fresh-runner workflow startup fix

[Run 40888955510](https://github.com/thewongphoto/SMA-indictor/actions/runs/40888955510)
passed **75 unit tests**, then stopped in Kivy initialization with
`FileNotFoundError` for `.local/kivy`. Its parent directory did not exist on the
fresh runner. Kivy calls `mkdir` rather than recursively creating parents.
Signing migration and APK packaging were not reached in that run.

The workflow now creates its configured Kivy/cache/artifact directories before
launching. The smoke runner does the same before importing Kivy. The original
exception was reproduced with a missing nested temporary path; validation uses
fresh directories instead of relying on existing workspace folders.
All **30 running Kivy UI groups passed** with those fresh paths after the fix.
Workflow YAML and shell syntax checks also passed. The 75-unit-test pass above
is from the supplied GitHub log; unit logic did not change in this fix.

Start a new workflow run on **main** to pick up the fix. Keep the one-time
signing-migration checkbox selected if you were attempting that setup: the
failed run did not reach it. Full GitHub/Xvfb/Android execution still needs the
new run; local UI checks use SDL offscreen rendering.

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
