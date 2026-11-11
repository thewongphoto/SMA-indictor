# Project instructions

## Platform direction

- The app targets **both Android and iPhone/iOS**. Design new tables, stored
  identities, data providers, cache policies, signal rules and scheduler contracts
  for both platforms. Keep OS-specific delivery and scheduling in adapters.
- Persist real session dates, IANA timezones, quotation currencies and UTC
  timestamps. Never identify live alert events only by a shifting row index.
- Live target/observed annual frequency uses exactly 365 calendar days: sum
  elapsed days between adjacent observable closes, including weekends/holidays,
  then crossings × 365 / observable calendar days. Retain warm-up/gap exclusion,
  exact Fraction ties and identical NumPy/mobile scoring. Always pass live dates
  through optimization, saved-result reconstruction and the guide. Date-free
  legacy/demo fixtures alone retain their old 252-session approximation.
  Live yearly view/backtest horizons also use 365 days per year; monthly presets
  remain calendar months. Invalidate derived optimizer choices by policy version,
  but never retune/delete saved SMA periods, colours, names or alert preferences.
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
- Android 0.10.0 adds user-authorized scheduled checks for saved live SMAs whose
  phone switch and at least one signal type are enabled. US: Tue–Sat 06:30;
  SGX: Mon–Fri 18:30, Asia/Singapore. Opening reminders: US Mon–Fri 21:30;
  SGX Mon–Fri 09:00, fixed Singapore time throughout US daylight saving changes.
  Opening reminders use the last adjusted close strictly ABOVE the saved SMA,
  as requested; EOD monitor remains strictly BELOW. Never substitute live prices.
  New opening-type preferences default On; preserve stored closing-type/line Off
  choices. Keep close jobs active for cache refresh even for start-only users.
  Native WorkManager binds a short headless Python service; do not replace it
  with a paused Kivy timer or a foreground transition followed by startService.
  The private bound service must run in a dedicated process: p4a kills that
  process on destruction. Check cancellation and report even Python startup
  failures; log native stage/cause classes without private exception messages.
  The background-test button exercises this same path, with no market request.
  Use per-slot unique
  native work and the durable region/due journal; never replay old session alerts.
  Keep closing job identities US/SG; opening identities US_START/SG_START and
  alert kind monitor_start are shared with iOS. Opening reminders expire after
  30 minutes; delayed older native slots must not borrow today's slot. A fresh
  closing fetch can verify an older holiday close; stale caches must not trigger
  opening reminders. Upcoming trading dates and reference close dates are distinct.
  iOS 0.11.0 adds a BGTaskScheduler/UNUserNotificationCenter adapter. Register
  native background handlers before application launch finishes. Use the shared
  daily job, real session dates and durable run journal; expiry stops further
  fetches/delivery. Never promise exact background execution on iPhone.
- Research notifications request a banner and sound, then stay in the system
  notification drawer/Notification Center. Preserve explicit OS quiet/disabled
  channel choices. The iOS adapter honors the same alert presentation contract
  with foreground banner/list/sound and the user's system/Focus preferences.
- SMA period labels use `SMA (X days)`; days mean trading observations. Custom
  names and numeric saved identities are unchanged. Page transitions are brief;
  archive/help sheets share the saved drawer. Native Back cancels optimization
  in place; stale completions must never dismiss a newer calculation overlay.
- Optimization draws the shared logo's actual strokes left to right on a
  continuous frame clock, revealing its plus at the upward price/SMA crossing.
  Keep GLSL uniforms floats even at 0/1 and effect matrices isolated from modal
  and capture canvases. Check rendered pixels, centering, loop continuation and
  cancellation. Mobile scoring yields CPU/GIL time without changing results.
- A saved SMA offers 12 colour presets. Keep automatic allocation separate from
  custom colour overrides; retain choices through archive/restore and upgrades.
- Startup availability probes use VOO once per provider lifetime. The live guide
  always uses Vanguard S&P 500 ETF (VOO), independently of the selected security.
  Its initial target is 4/year and investment horizon Max. Guide horizon changes
  reuse the lesson's data and SMA without fetching or optimizing again; use the
  same presets, animated Custom input and keyboard handling as real backtesting.
- Chart presets include 3M/6M/9M before 1Y. Live ranges use actual calendar months
  for month presets, with month-end/leap-day clamping. Year presets use exactly
  365 days per year; both start at the first session on/after the cutoff.
  Chart zoom and investment horizons remain independent of full-history scoring.
  Chart descriptive copy is currency plus adjusted daily close and dividend/split
  inclusion; the old usable-comparisons paragraph above backtesting is removed.
- Company and ETF issuer logos are bundled PNGs, with no runtime logo API calls.
  Resolve logos for legacy cached identities too; keep issuer metadata portable
  and never substitute a guessed brand for an unknown fund. Preserve asset credits.
- These are target times, not a guarantee that Android or iOS will execute
  background work at an exact instant. iOS suspends background apps and native
  OS scheduling must be implemented and tested separately.
- Keep base/mobile dependencies in requirements.txt and desktop Yahoo
  dependencies in requirements-desktop.txt until mobile packaging is validated.
  A desktop update does not authorize an APK tag/build.
- iPhone builds use the pinned official kivy-ios toolchain, mobile JSON client,
  pure Python HTTPS dependency wheels and bundled tzdata. Stage an allowlist:
  never include local data, secrets, desktop environments or signing files.
  The private download is an unsigned arm64 Xcode kit; the user signs locally
  with their Personal Team. Never claim a kit/IPA installs directly from Safari.
  Keep its bundle identifier and signing team stable to preserve installed data.
  The kit upload is gated on native device/simulator builds and fresh simulator
  launches. Linux fixture checks do not establish Apple signing/device behavior.
  A cold iOS background launch must stay in the pure native/Python entry path
  until foregrounded. Never import the Kivy app/window or use OpenGL there.
  Run the verified native-source preflight before kivy-ios. Its legacy OpenSSL
  HTTP endpoint failed with 504; use the immutable official source commit and
  pinned checksums in ios/native-sources.json. Never disable TLS/checksums.
- Chart changes use the first/last finite adjusted closes inside the fractional
  visible bounds, without interpolation or network calls. Percent is relative
  to the left close; use quote currency. Match both arrows/values to direction,
  with neutral flat/empty states. Presets say PAST 3M/etc; pinch uses actual EOD
  endpoint dates. Keep full dates readable on narrow phones.
- The approved app icon is Crosspoint (proposal 1), corrected so the turquoise
  price rises from below to above the orange SMA with a steeper recovery. Its shared master is the
  opaque 1024px RGB PNG at sma_analyzer/assets/app-icon.png. Native platforms
  apply their own masks; keep master corners navy, and Android adaptive artwork
  inside the safe circle. Export iPhone AppIcon sizes at build time. Preserve
  regenerated PNG dimensions, mode and decoded pixels across hosts; compressed
  PNG bytes can differ with the host encoder. Keep strict resource hashes when
  verifying copies of the same compiled app in the signing kit. Preserve
  compiled CFBundleIcons metadata and icon-resource hashes through the Personal
  Team signing kit. All Info.plist/verifier background task identifiers derive
  from schedule.JOB_IDS; never hardcode the old two closing-only identifiers.
  Launcher icons and launch images are separate: explicitly set Android's
  presplash and replace the iOS template's icon.png/launch storyboard as well.
- Both mobile workflows prefetch verified GitHub source archives from the
  official codeload host; the archive frontend returned HTTP 504 for PyJNIus and
  Kivy. Keep versions/commits/checksums in scripts/native-archives.json aligned
  with the pinned toolchains. Android needs the original recipe filenames and
  a completion marker created only after verification. All iOS CLI subcommands
  use scripts/ios_toolchain.py so even Kivy's temporary SDL version probe reads
  the verified cache. Do not replace release assets with Git snapshots: their
  generated contents can differ. Save verified sources before native compilation.
- Sustained loading checks use elapsed-time drawing cycles and update gaps,
  not a minimum FPS/frame count. Exercise a slow CI frame clock too; preserve
  checks for one-cycle stops, pauses and incorrect speed during real scoring.
- Mobile uses the portable Yahoo JSON transport for the yfinance search/chart
  subset; it does not import pandas/curl_cffi or launch desktop helpers.
  p4a installs generic modules with --no-deps, so buildozer.spec must list the
  complete requests dependency closure. Preserve app signing/package identity.
- The Android UI iteration after 0.8.0 adds smooth pinch input, per-security SMA
  colors, calendar axis labels, persistent analysis reuse, neutral visible data
  labels and a scrolling request log. Its live guide must use downloaded history.
  USD backtest values use quotation-price ratios, excluding currency movements;
  do not imply that an FX conversion/history API has been integrated.
- Search and preferences are stages of the same builder Screen. Reveal the
  target/Optimize group after selection; changing parameters reuses that stage.
  Saved custom names are plain text, persist through archive/restore, and do not
  change saved identities, periods, colors or signal deduplication keys.
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
- Merged builder/name flows: .venv/bin/python -m scripts.smoke_ui_flow
- Motion, drawers and cancel races: .venv/bin/python -m scripts.smoke_ui_motion
- Sustained spinner, colours and ETF logos: .venv/bin/python -m scripts.smoke_ui_color_logos
- Live diagnostic (network required): .venv/bin/python -m scripts.check_yahoo
- Use SDL_VIDEODRIVER=offscreen and LIBGL_ALWAYS_SOFTWARE=1 for headless Kivy.
  UI scripts isolate their data and do not use a user's live cache.
- Distinguish fixture validation, live Yahoo connectivity and physical-device
  validation when reporting results. Keep START_HERE_MAC.md current.
