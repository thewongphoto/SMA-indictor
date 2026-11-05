# Project instructions

## Platform direction

- The app targets **both Android and iPhone/iOS**. Design new tables, stored
  identities, data providers, cache policies, signal rules and scheduler contracts
  for both platforms. Keep OS-specific delivery and scheduling in adapters.
- Persist real session dates, IANA timezones, quotation currencies and UTC
  timestamps. Never identify live alert events only by a shifting row index.
- Keep existing simulated saves and their archive distinct from Yahoo history.
  Never relabel synthetic dates/prices as real data.
- Yahoo data is currently for private personal use. Cached market histories,
  exports, tokens, cookies and signing credentials do not belong in Git.

## Current desktop scope

- The current desktop iteration tests API retrieval through user interaction:
  one startup check, submitted search, selection/View when needed and explicit
  refreshes. Do not add persistent desktop background services, periodic fetches
  or notification delivery tests. A short-lived request-isolation process is
  allowed to keep a blocked/crashing native dependency from closing Kivy.
- Normal launcher use must select Yahoo mode and start without synthetic prices.
  Explicit --demo is the only launcher route into the local simulation.
- Treat security alerts as unresolved until the exact file and wording have
  been investigated; do not disable protection or presume a false positive.
- The user authorized the Android 0.8.0 Yahoo data-test APK and build tag.
  Its scope is interactive search/history, persistent caching, visible failures
  and copyable request logs. Background scheduling and notification delivery
  tests remain deferred.
  Preserve the future schedule definitions: US listings Tue–Sat 06:00
  Asia/Singapore; Singapore listings Mon–Fri 17:30 Asia/Singapore.
- These are target times, not a guarantee that Android or iOS will execute
  background work at an exact instant. iOS suspends background apps and native
  OS scheduling must be implemented and tested separately.
- Keep base/mobile dependencies in requirements.txt and desktop Yahoo
  dependencies in requirements-desktop.txt until mobile packaging is validated.
  A desktop update does not authorize an APK tag/build.
- Mobile uses the portable Yahoo JSON transport for the yfinance search/chart
  subset; it does not import pandas/curl_cffi or launch desktop helpers.
  p4a installs generic modules with --no-deps, so buildozer.spec must list the
  complete requests dependency closure. Preserve app signing/package identity.
- The Android UI iteration after 0.8.0 adds smooth pinch input, per-security SMA
  colors, calendar axis labels, persistent analysis reuse, neutral visible data
  labels and a scrolling request log. Its live guide must use downloaded history.
  USD backtest values use quotation-price ratios, excluding currency movements;
  do not imply that an FX conversion/history API has been integrated.
- Keep authentication values and raw responses out of request logs. Record
  app actions, HTTP outcomes and cache hits separately and preserve log upgrades.
- Live charts, SMA signals, lessons and return comparisons use dividend/split
  **Adj Close**. Fetch/store Close and corporate actions too, but never fill a
  missing adjustment with ordinary Close or add cash dividends on top of the
  adjusted-return calculation. A dividend/revision requires a full resync to
  keep historical adjustment factors consistent. Reuse legacy cached Adj Close
  only when complete; otherwise fetch MAX without deleting saved SMA parameters.

## Useful checks

- Unit tests: .venv/bin/python -m unittest discover -s tests -v
- Offline UI: .venv/bin/python -m scripts.smoke_ui
- Yahoo UI with synthetic transport: .venv/bin/python -m scripts.smoke_yahoo_ui
- Mobile JSON/UI fixtures: .venv/bin/python -m scripts.smoke_mobile_yahoo_ui
- Gesture/live-screen refinements: .venv/bin/python -m scripts.smoke_ui_refinements
- Live diagnostic (network required): .venv/bin/python -m scripts.check_yahoo
- Use SDL_VIDEODRIVER=offscreen and LIBGL_ALWAYS_SOFTWARE=1 for headless Kivy.
  UI scripts isolate their data and do not use a user's live cache.
- Distinguish fixture validation, live Yahoo connectivity and physical-device
  validation when reporting results. Keep START_HERE_MAC.md current.
