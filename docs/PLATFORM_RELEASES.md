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
