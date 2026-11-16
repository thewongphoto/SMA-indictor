# Web and Android releases

The iPhone app is the Vercel website / Home Screen web app. A web-only fix can
deploy independently. Native iOS builds remain paused.

| Change | Release | Required checks |
| --- | --- | --- |
| Web screens, browser gestures or web-only setup | Bump `web/package.json`, lockfile and service-worker cache; push `main`. No `apk-v` tag or native version change. | Web production build, JavaScript/Python adapter tests, affected Chromium/WebKit flows and a review against the native reference. |
| Android screens or native scheduling/packaging | Bump native version and `buildozer.spec`; push `main` and a new `apk-v…` tag. | Complete native tests/UI gates and final APK/signing verification. Check web behaviour if affected. |
| Shared calculations, assets or an API consumed by both | Coordinate both platforms; keep old APK/server compatibility. | Both clients' relevant tests and all required native release gates. |

Vercel deploys pushes to `main`. The [Android workflow](../.github/workflows/android-debug.yml)
already starts only on `apk-v*` tags or manual dispatch. There is no need to
weaken its compilation, signing or verification steps to save time on a web-only
release: simply do not start that workflow. The [web workflow](../.github/workflows/web.yml)
continues to validate the browser app. A pre-existing Android build is independent
of a later web-only commit.

## Impacts and compatibility

- Web users receive fixes after deployment/reload; installed APKs keep their
  current version until updated. Different web/Android version numbers are expected.
- Skipping native compilation saves build time and GitHub Actions usage. It
  produces no APK and cannot fix an Android-only problem.
- Saved lines, colours and alert switches stay in the existing device storage.
  A web deployment must not clear IndexedDB/local storage. A web UI version bump
  currently invalidates unsaved optimizer-choice caches; their next calculation
  may run again. Saved SMA periods are retained.
- An already-open/offline Home Screen app can keep older code until it reloads.
  Keep server APIs compatible with both older web clients and installed APKs.
- A folder name alone does not establish scope. Android also calls the Vercel
  contact-email API. Shared Python is copied into the browser runtime at build
  time, while an installed APK keeps its bundled copy. Changes to those contracts
  require checks for both platforms, even if the edited file is under `web/`.
- Web rollback does not roll back an APK. Database/API migrations must remain
  safe for clients on both sides of a deployment or rollback.

## Review before every UI release

Review the affected journey on both implementations: entry point, selected
security, target defaults and presets, Custom validation, calculation timing,
cancel/Back, saved state, chart markers/inspection and narrow-screen layouts as
applicable. Capture both sides and state which behaviours were checked. Record
intentional differences such as OS keyboard, installation and notification UI;
do not describe every screen as aligned after reviewing only a chart.

For the security/preferences journey:

```sh
python -m scripts.smoke_ui_flow
python -m scripts.smoke_builder_web
python -m scripts.check_builder_parity
```

The first exercises the actual Kivy builder with controlled mobile HTTP; the
second runs Chromium and WebKit against controlled browser responses; the third
compares their observed stage title, default target, presets, same-screen
selection and absence of automatic optimization. Real Pyodide scoring and chart
interaction remain covered by `scripts.smoke_local_web` and
`scripts.smoke_chart_webkit`. Artifacts retain captures and machine-readable
reports. These checks do not establish behaviour on physical phones.

## Web 0.18.2 review

Native reference: Android source 0.18.1, unchanged by this release. The web builder
now stays on **Set your preference** after selecting a security; its initial
target is 12, matching the native fresh-session default. Both offer 4/6/12 and
Custom, reuse downloaded history, and calculate only on explicit submission.
The selected security/logo stays visible. Charts appears after calculation;
Back returns to preferences and Cancel stays in place. Chart Custom returns to
the same preference stage. The selected company control focuses search and the
Charts tab marks the builder as active. Tests also cover failed history selection, cancellation
before job creation returns, and 320/390/430-pixel layouts.

The existing chart suite checks shared fonts/logos, currency labels, teal price
strokes, exact crossing markers, close/SMA inspection and zoom in both browser
engines. This is a review of these affected flows, not a claim that all native
and web screens or OS delivery behaviour are identical.

## Android 0.18.2 startup review

The recorded Android issue showed Home and then Search before the welcome arrived.
The native invitation now occupies the first UI frame after the platform splash;
it does not wait for service readiness and has no modal fade. You can type or Skip
while email setup is checked; sending still requires server confirmation. Returning
users go directly to Home, and late replies cannot reopen a skipped invitation.
The native first-frame fixture holds both email and market workers and checks
render order, disabled sending, Skip, retry and preserved values. Existing signup
fixtures retain add/change/remove and server-acceptance checks.

The browser already owns the opening route and shows an opening state while
checking readiness, so it does not open Home and then interrupt another screen.
Its form timing is unchanged in this Android-only fix. Field purposes, optional
Skip, confirmation before completion, data retention and API protocol remain the
same. The Android system splash and Python/SDL initialization still precede its
first UI frame; these fixtures do not measure physical-device startup speed.

## Shared 0.19.0 custom-history review

Both clients now expose the same history input before the first calculation and
after a result. The reviewed journey covers All available, 10/5/3-year presets,
invalid/custom dates, mini-chart/readout, cancel/reset, no automatic requests or
calculations, stale Save protection, explicit recalculation and screen 24's two
save choices. Update retains identity/name/colour/alert choices; New retains both
and starts the new line's alert/type switches on. Home, saved lists, Alerts,
chart/status and notification labels distinguish frozen custom windows while
leaving default lines untagged.

The native picker uses the shared scrolling bottom sheet and text date fields;
the web picker uses the browser's native date input/keyboard. Both use standard
app styling, readable phone layouts and explicit Cancel/Apply. The existing
chart regressions retain markers, touch inspection and zoom checks; full-price
charts and independent investment horizons are preserved. The new browser test
runs the actual shared Python calculations in Chromium and WebKit. Native
screenshots and browser captures were reviewed, including the absence of
duplicate year labels on Home. Scope is this history journey and the existing
chart/builder regressions, not every screen or physical OS behaviour.

## Shared 0.19.1 editing and Settings review

Native Charts now follows web's section order: chart/ranges, Signals per year,
Saved lines and backtesting. The duplicate native Saved/Selected/Optimal SMA
card is detached from the visible screen. Saved lines → Edit owns the name and
12-colour choices, followed by Archive line and Cancel. Opening Custom preferences
preserves the current target/result, while genuine parameter edits still require
calculation. Existing chart gestures, markers and saved-window behaviour remain
covered by the retained suites.

The affected native flow was reviewed at 320/390 widths and in light/dark themes.
Tests exercise the actual inline Edit control, Done, Cancel, Archive and restore;
Cancel leaves the stored record/colour unchanged, and Archive keeps the last
saved settings rather than its draft. The native editor scrolls on shorter
viewports; web retains its own bottom-sheet/keyboard behaviour.

Both Settings pages omit Market Data. Web export/import/restore remain in a
Saved lines card; the Owner server setup footer link is removed. Owner setup
continues to work directly at `/setup` with its existing authentication.
Chromium/WebKit capture and check these removals, section order and backup
availability. Native settings captures confirm the removed card. This review
covers these edits and related existing flows, not global UI equivalence or
physical-device notification delivery.

## Android 0.19.2 full-guide review

The iPhone web 0.19.1 guide is the reference. Native now reuses the normal Charts
and backtest components with the same introductory text and Finish action:
company/price/change, SMA status, full chart and inspection, range chips,
signals/history and recalculation, three equal-budget comparisons, contribution
and date summary, ending values/gains/bars, random-sample statistic, disclaimer
and All upward crossings. Default target is 4/year, chart 1Y and horizon Max.
Frequency/history edits calculate explicitly; horizon changes reuse data/SMA.

The guide uses a temporary model/store and suppresses saving and notification
schedule changes. Finish, Back and tab navigation restore the original analysis,
target, zoom and horizon. A late loading completion cannot reopen a finished
lesson. Native fixture checks cover these paths, chart-history refinement and
opening/returning from the crossing list; existing full native gates remain.

The native and actual-Pyodide Chromium/WebKit guides receive identical controlled
adjusted prices. Their displayed SMA period, latest price, default horizon and
three ending values are compared, alongside the information/controls present.
Native dark/light guide captures and browser phone-width captures are reviewed.
Native Back and web browser/Finish navigation use their respective app controls;
their OS keyboard/chrome differ. This establishes the reviewed guide flow, not
global platform equivalence or physical-device scheduling. Native source/tag
advances independently to 0.19.2; the web app remains 0.19.1.

## Crosspoints 0.20.0 naming review

Android and iPhone web display **Crosspoints** in the welcome/loading screens,
application/browser title, launcher/Home Screen metadata, diagnostics and
test/owner-email branding. The original icon is retained. Technical package and
bundle identifiers, signing identity, local databases/storage keys, manifest ID,
API routes, frozen email requests and notification keys remain compatible.
SMA continues to name the moving-average indicator and saved lines.

The affected native welcome/Settings captures and browser welcome are reviewed
at phone widths. Actual Chromium/WebKit checks confirm the browser title, Apple
Home Screen title, manifest name/short name, optional Skip and version display.
Existing signup tests exercise add/modify/remove/retry with delivery mocked;
server tests retain frozen-payload safety and fixed-recipient forwarding.
The full native UI gates and existing guide/chart regressions remain required.
This review covers the rename and retained flows, not physical-device launch or
global UI equivalence. An existing Home Screen label can be cached by iOS.

The requested `crosspoints.vercel.app` address is not claimed by a Git push.
Assignment needs the owner's authenticated Vercel account and an available
domain. The [migration guide](CROSSPOINTS_DOMAIN.md) retains the old APK contact
endpoint, transfers saved web parameters explicitly, and updates Supabase's
scheduled website URL with the existing keys.
