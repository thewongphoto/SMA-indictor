# Validation and build status

Current source: **0.20.0**. The matching Android build tag is **apk-v0.20.0**.
Native build completion must be checked in
[GitHub Actions](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml).
A published tag or uploaded diagnostic ZIP alone does not prove an APK exists.

Crosspoints 0.20.0 changes the display name on Android and iPhone web. It retains
package/signing identity, device storage and notification identities. The affected
review covers the welcome page at narrow widths, browser/Home Screen metadata,
Skip, Settings version, diagnostics and owner-email branding. Controlled signup
tests send no real email. See [the naming review](PLATFORM_RELEASES.md) and
[the separate domain migration](CROSSPOINTS_DOMAIN.md).

Local 0.20.0 validation passed all 13 native UI gates, 370 Python tests (two
optional skips), 37 JavaScript tests and the production web build. Actual
Chromium/WebKit checks passed the renamed welcome, browser/Apple/manifest names,
320/390-width layouts, Skip and Settings version. Signup add/change/remove/retry
fixtures passed; both browser guides still matched the native price/SMA/backtest
observations. Native welcome and browser captures were reviewed. These are
controlled checks; final native compilation/signing and a physical-phone launch
remain separate from local validation.

Android 0.19.2 replaces the simplified guide with the same detail/backtest
components as the main native Charts screen. The affected review covers the
introduction/Finish action, price/change/status, chart/ranges/legend/gestures,
signals and history selection, complete comparisons/gains/random statistic and
crossing list. Native tests exercise explicit frequency/history recalculation,
independent horizons, Custom, save protection, restore of the original analysis
and cancellation before loading completes. Chromium/WebKit guide fixtures use
the same adjusted closing prices and compare their actual displayed SMA period,
price and ending values with the native observations. Captures are retained in
`guide-ui`, `guide-web` and the native guide captures in `ui-0.9` diagnostics.
Physical-phone behaviour is separate from these controlled fixtures.
Local validation passed all 13 native UI gates and all 370 Python tests (two
optional skips). The final guide rerun also passed after the Android-private
temporary-storage check and light/dark captures. Actual Chromium and WebKit
guide observations matched the native SMA period, price and three ending values.
The web guide UI stays at 0.19.1; its new observation test does not change web
behaviour. See [the platform review](PLATFORM_RELEASES.md).

Release 0.19.1 removes the duplicate native SMA card, places Signals per year
before Saved lines, and adds Archive line/Cancel to the native combined editor.
Native regression checks use the visible Saved lines editor for name/colour
changes and verify that Cancel keeps the saved record unchanged and Archive
discards drafts while preserving settings for restoration. Existing motion,
colour, offline, library, transport and alert gates remain required. The web
history suite checks the same section order on Chromium/WebKit, absence of the
Market Data card and owner setup footer link, and retained backup controls.
Host validation: 370 Python tests (368 passed, two optional skips), 37 JavaScript
tests, 13 native UI gates, eight browser suites, production web build, SQL
fixtures and the native/browser builder comparison. Captures of the affected
native and browser screens were reviewed; physical-phone behaviour is not
established by these fixtures. Data/schema, optimization and signal rules remain
unchanged. [Affected UI review](PLATFORM_RELEASES.md).

Release 0.19.0 host validation covers frozen custom history, real engine
guardrails, slice-only optimizer scoring, cache separation, full-series chart
reconstruction, old SQLite migration/IDs, independent colours, archive/restore
and unchanged default alert keys. **370 Python tests completed (368 passed,
two optional skips)** and **37 JavaScript tests passed**. All 13 local native
UI gates pass, including the new history flow and the updated compact-layout
check accounting for exactly one additional row. Native/WebKit/Chromium captures
review the default/picker, narrow dates, stale result, Update preservation, New
alerts on, Home labels and restart state. The observed builder parity check
also passes.

The web production build, contact SQL fixtures and all eight browser smoke
suites pass. The new custom-history suite uses actual Pyodide/NumPy on both
engines, with intercepted market responses and no service-worker interception;
separate existing tests retain offline-runtime coverage. Existing chart fixtures
continue to check named saved lines, touch inspection, pluses and shared styles.
These checks send no real email/push and do not establish physical-phone keyboard,
launch performance, signing or scheduled delivery. Final APK verification remains
a separate required Actions step. [Feature and review](CUSTOM_PRICE_HISTORY.md).

Android 0.18.2 adds cold-lifecycle startup checks with held email/Yahoo workers:
the first rendered frame is an opaque, topmost welcome before readiness completes;
typing/Skip work immediately, late replies never interrupt Search, offline retry
retains input and submissions use an independent worker. Returning users retain
their email and open Home, while an explicitly disabled endpoint makes no request.
These are controlled Kivy/transport checks, not measured phone launch times.
All 12 local native UI gates passed, as did 363 Python tests (361 passed, two
optional skips), the web production build, 32 JavaScript tests, browser signup
checks and the Chromium/WebKit builder comparison against the native reference.

Web-only 0.18.2 keeps the native source/tag unchanged. Its production build,
32 JavaScript tests, six Python web-service tests and seven browser smoke suites
cover the builder, real Pyodide calculations, charts, saved/offline state,
signup and owner setup. A fresh native builder run and observed native/browser
comparison cover the affected preference flow. See the [release scope and
parity review](PLATFORM_RELEASES.md). This release requests no new Android build.

Release 0.18.1 host validation covers password-free opening with and without
configured owner credentials, public market/device input validation, protected
owner diagnostics and legacy worker data, cross-origin write rejection,
owner login/logout and safe return navigation. Browser fixtures also cover
saved-data reopening, cold offline calculations, optional signup and WebKit
chart interactions. All 363 Python tests completed (361 passed, two optional
skips), all 32 JavaScript tests passed, and all 11 native UI gates passed.
The production web build and six browser smoke checks passed. These tests send
no real email or push notifications.

Release 0.18.0 host validation ran **363 Python tests (361 passed, two optional
checks skipped)** and **32 JavaScript tests**. All 11 native UI gates passed,
including the new inset/keyboard divider regression on all four pages. Real
Chromium touch input checks close/SMA inspection, two-finger zoom, pinch release
and hidden-line markers against the shared Python results. WebKit checks actual
touch capture, dragged inspection, multiple saved SMA values/intersections, both
teal themes, native brand assets and 320/390/430 layouts. These are controlled
fixture tests, not physical-device acceptance or live Yahoo observations.

Release 0.17.0 host validation ran **361 Python tests (359 passed, two optional
checks skipped)** and **23 JavaScript tests**. Real PostgreSQL fixtures verify
add/modify/remove/re-add, source/version and message snapshots, duplicate/stale
requests, private-registry access, expiry and migration reruns. Browser/native
signup fixtures cover failed removal, persistent retry IDs, local address cleanup
and re-add. All 11 native UI gates passed, including offline/library, Yahoo
fixtures, redesign, signup, keyboard/gesture/motion, slow-clock colours/logos and
notification-job checks. Email calls remain mocked; no real delivery was exercised. Rerun the
protocol 2 SQL as described in the [email guide](EMAIL_SIGNUP_SETUP.md).

Release 0.16.0 validates optional email forwarding with **359 Python tests
(357 passed, two optional checks skipped)** and **18 JavaScript tests**, plus
production builds, real Pyodide/browser flows, welcome validation/retry/Skip
fixtures and isolated PostgreSQL claims, quotas, counts and migration reruns.
Email-provider calls are mocked; these tests send no emails and do not establish
live Gmail delivery. All 11 local native UI gates passed, including offline/library flows, both Yahoo
fixtures, refinements, flow, redesign, signup, motion, slow-clock colour/logo and
notification-job checks. The Android workflow adds the signup fixture to its
retained gates. Configure Resend and perform the manual
acceptance check in the [email guide](EMAIL_SIGNUP_SETUP.md).

Release 0.14.2 rebuilds the Android Charts, backtest, Settings, search, Home,
edit-line, calculating and first-open screens to the November design. Its UI
gates were updated to the new copy and layout (for example chip horizons
instead of dropdowns) and wait on the animation they check rather than a fixed
frame count; calculations and stored data are unchanged.

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

For 0.15.0, the 354-test Python suite passed with two optional skips. The
new browser workflow runs real Pyodide/NumPy and compares its result with
Python, then checks cold offline backtesting, local persistence, backup import
and setup UI. Server fixtures compare signal rules and all four schedules with
native Python, and check claims, stale data and subscription expiration.
Live Supabase SQL setup and physical iPhone push acceptance remain owner steps
in the [free setup guide](PRIVATE_IPHONE_INSTALLATION.md).
