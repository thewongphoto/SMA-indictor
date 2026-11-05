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
  refreshes. Do not add desktop background workers or notification delivery tests.
- Background API/notification testing is deferred to a user-authorized APK stage.
  Preserve the future schedule definitions: US listings Tue–Sat 06:00
  Asia/Singapore; Singapore listings Mon–Fri 17:30 Asia/Singapore.
- These are target times, not a guarantee that Android or iOS will execute
  background work at an exact instant. iOS suspends background apps and native
  OS scheduling must be implemented and tested separately.
- Keep base/mobile dependencies in requirements.txt and desktop Yahoo
  dependencies in requirements-desktop.txt until mobile packaging is validated.
  A desktop update does not authorize an APK tag/build.

## Useful checks

- Unit tests: .venv/bin/python -m unittest discover -s tests -v
- Offline UI: .venv/bin/python -m scripts.smoke_ui
- Yahoo UI with synthetic transport: .venv/bin/python -m scripts.smoke_yahoo_ui
- Live diagnostic (network required): .venv/bin/python -m scripts.check_yahoo
- Use SDL_VIDEODRIVER=offscreen and LIBGL_ALWAYS_SOFTWARE=1 for headless Kivy.
  UI scripts isolate their data and do not use a user's live cache.
- Distinguish fixture validation, live Yahoo connectivity and physical-device
  validation when reporting results. Keep START_HERE_MAC.md current.
