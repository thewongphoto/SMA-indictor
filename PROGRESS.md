# Prototype handoff

## Fresh GitHub runner startup fix

- Run 40888955510 passed all 75 unit tests, then failed before UI startup:
  FileNotFoundError for the configured .local/kivy directory. Kivy's mkdir
  could not create its absent .local parent on a clean checkout. No signing or
  APK build steps were reached.
- The workflow explicitly creates KIVY_HOME/XDG_CACHE_HOME/artifacts before
  launch. The smoke runner also prepares configured directories before Kivy
  imports, so standalone execution works with fresh nested paths.
- Original failure reproduced with an absent temporary nested KIVY_HOME.
  All 30 running UI groups then passed using fresh temporary nested Kivy/cache
  directories; workflow YAML/shell syntax checks passed. The supplied GitHub
  log already records 75 passing unit tests before the startup failure.
  App code, SMA math, Android behavior and signing identity are unchanged.

## Android corrections — version 0.2.1

- User tested the installed prior APK: generic Android test notification works.
  Back, email/EOD editing, saved menu/discovery and system-bar overlap were
  reported failing. Do not label these new corrections as phone-verified yet.
- Native Back now routes through a page stack, dismissing editor/modal/sheet
  before navigation. Exit only on Parameters. Results navigation resets its
  canonical parent stack, including after returning from Parameters/Settings.
- AndroidWindowBridge reports overlapping system bars/cutout/IME relative to
  SDL's actual surface. DeviceFrame sizes/positions the entire app, including
  the saved sheet, without double-counting OS-resized/inset surfaces. Desktop
  minimum dimensions are no longer imposed on Android. EditingField preserves
  focus through touch replay/reflow; focused fields scroll above the keyboard.
- Saved menu icon and text both respond; sheet geometry follows the safe root.
  Parameters displays all saved rows across scopes, with View instead of Hide.
  Titles are clickable. View restores exact parameters, full-history statistics
  and selected overlay without optimizing, including older above-cap periods.
- Existing SQLite commits/private user-data path/data version are retained.
  A subprocess saves all-scope rows, channel/visibility/recipient settings and
  delivery records, then calls os._exit; reopening verifies persistence. The old
  current-scenario-only discovery could make rows appear missing after launch.
- Signing restores ANDROID_DEBUG_KEYSTORE_BASE64, with the original cache as
  migration fallback. It verifies ANDROID_SIGNING_SHA1 and never generates a
  new key on a cache miss. The one-time workflow checkbox plus temporary scoped
  SIGNING_ADMIN_TOKEN can persist the existing cached key in Actions secrets.
  User must do this browser setup; current tools cannot set repository secrets.
  Missing original key cannot be reconstructed from its fingerprint. Do not
  generate a replacement or uninstall the user's app as a routine workaround.
- 75 unit tests pass, including eight new persistence/view/inset/signing checks.
  Real keytool restore round-trip passes; both Java bridges compile against
  actual Android API 35/Google 21.4.0 classes. Focused Kivy regression checks pass.
  The full latest UI run passes all 30 groups, including four new Android
  regression groups. Details are in docs/ANDROID_TEST_STATUS.md.
- docs/ANDROID_RELEASE_CHECKLIST.md is the saved device regression list;
  docs/ANDROID_SIGNING.md explains permanent fingerprint preservation. The APK
  workflow now runs unit and Kivy UI checks before native packaging and uploads
  their reports. It needs a fresh run on main; no phone/emulator is attached.
- No mock data, math, Gmail sender, notification rules, database schema or
  background-work behavior changed. No real email was sent. Next: retain the
  original signing key, build 0.2.1, install over the existing APK and execute
  the device checklist. No live-price or background-scheduler work is authorized.

## Completed

- Pure SMA engine with documented crossing/equality/gap rules, adjusted annual
  targets over observable history, automatic cap and shorter-period tie-break.
- Fixed-seed five-year (1,260-session) generators for two fictional counters × three scenarios.
- Native Kivy canvas price/SMA overlays and black-outlined plus signs at calculated event indices.
- Preset/custom target controls, background calculation/loading state, summary
  cards, full selected-result crossover table, and helpful invalid/empty states.
- SQLite saved lines, per-counter/scenario scoping, duplicate protection,
  multiple overlays, persistent saved visibility, and removal.
- Responsive portrait column, vertical scrolling, and beginner run instructions.
- Drag-to-zoom in either direction, immediate green start/red end boundaries,
  translucent selection, auto-scaled visible y-range, and a top-right Zoom out
  button that appears only while zoomed. Touches in the plot bypass scroll delay;
  page swipes outside the plot and mouse-wheel scrolling remain available.
- 67 standard-library tests passed; 26 running Kivy smoke groups passed.
  Screenshots generated in ignored `artifacts/`. No failed or skipped checks.

## Decisions to preserve

- Mock data only; five-year default (1,260 sessions). Seeded prefixes and the
  generator version are preserved so prior saved periods remain available.
- Active cap: min(floor(H/2),252) through H=756; H-504 above that.
- Require at least H-cap actual observable comparisons, excluding warm-up/gaps.
- Rank by annual-frequency error over all observable history; exact ties use
  shorter SMA. Display one adjusted actual frequency, plus count and coverage.
- Preserve crossing equality/gap rules, chart zoom behavior, and local saved
  lines. Older periods above the cap remain labelled and viewable.
- Cloud tasks are isolated: use the existing checkout; no worktree unless requested.

## Known limitations / remaining work

- LinkedIn source returned HTTP 403; implementation follows the supplied prompt.
- Desktop UI rendered and exercised through SDL offscreen/Mesa, not a physical
  Android device. Clipboard cutbuffer warnings in this headless environment are
  nonfatal; no clipboard integration was verified.
- Short usable histories can give unstable annualized rates; targets may be
  unattainable. No profitability or future-frequency inference.
- No dates/calendar, adjustments, panning, pinch zoom, live data or background EOD scheduling.
  Debug APK configuration is present; successful native compilation/device checks remain pending.
- Active result/dropdown selections reset on restart; saved lines persist.
- Future genuine histories need performance profiling and schema migrations.

## Frequency policy: integrated into the running app

- `sma_analyzer/policy.py` contains the active automatic cap, coverage counting,
  and exact annual rate. `engine.optimize_sma` enforces the policy for the UI,
  model, and explicit candidate lists.
- The UI shows adjusted frequency only, usable comparisons/years, candidate cap,
  annual target difference, and an honest unmatched-target message.
- `experiments/observable_frequency.py` is the independent pre-integration
  reference. Production code does not import it. The comparison runner checks
  active results against that reference across all scenarios/targets.
- 67 unit tests and 26 running Kivy smoke groups passed in the current version,
  including the active five-year Sideways result: SMA 254, 125 crossings / 1,006
  comparisons, 31.31/year. Scenario, target, zoom, save/load and error checks passed.
- `APP_SUMMARY.md`, README and Mac instructions now describe active behavior.
  The evaluation report is retained as a historical pre-integration record.
- Mock history is now five years; generator seed/version remain unchanged. The notification update adds an
  additive SQLite migration for flags/history/settings/delivery records.
  Existing saved periods are preserved; those above the cap are labelled as
  outside the current search limit.
- Remaining: genuine data, Android device validation
  and packaging are separate subsequent tasks.

## Approved interface release

- Five-year mock history is active, with 1Y as the default chart view. The
  rounded timeline selector offers 1Y/3Y/5Y/Max; insufficient 3Y/5Y choices are
  omitted. Both the text and downward arrow are clickable. Choosing a preset
  resets custom zoom; Zoom out restores that preset. New data resets to 1Y.
- Optimization, cards and the full-history crossing table are independent of
  timeline/zoom. Markers and SMA drawing use the full calculated arrays.
- The Optimal SMA card and save/hide actions now span the area above the chart.
  Below it are two frequency cards; the crossing count moved into section 03.
- Chart and legend use a shared plus-sign drawing with a thin black border.
  Legend line swatches match actual series colors and have no color prefixes.
- `docs/ui-current.png` is a screenshot of the working app; `ui-preview.png`
  remains the approved illustrative design reference.

## Saved-line and notification enhancement

- Heart save/unsave controls (grey outline/red fill), chart-matched saved-row
  swatches, compact right-aligned hide/heart actions, and independent On/Off
  phone/email buttons. Period colours stay stable when overlays are hidden.
- Global last-10 distinct unsaved history with restore popup; only saved then
  unsaved entries qualify. Oldest entries are discarded. Restore preserves
  scope, period, target, visibility and channel flags.
- Bottom settings with native canvas phone/mail icons and rounded switches,
  persistent recipient/type settings, email syntax/missing-address validation.
- `notifications.py` contains pure EOD Buy/Monitor rules using the existing
  engine and an optional lazy native Android local notifier. Preview is default
  and email initially stayed preview-only. The later authorized Android/Gmail
  work is recorded under the current stop point below. No SMTP, domain or
  background EOD scheduler was added.
- Manual session preview / Android test / enabled-EOD delivery buttons. Persistent
  successful-send deduplication, failure retry and clear desktop limitation.
  There is no automatic/background EOD arrival source or remote push service.
- 67 unit tests and 26 running UI groups pass, including real window clicks on
  the heart/history/switches, fake Android delivery and duplicate suppression,
  actual subject/body text, migration, ten-entry pruning, restore and five sizes.
- `docs/NOTIFICATIONS.md` explains novice testing, exact templates, limitations
  and future device permissions. Settings and saved-line screenshots are linked
  from the GitHub preview page. Physical Android delivery remains unverified.

## Separate-screen release

- Native ScreenManager: parameters (launch), results (on successful optimization),
  full crossovers and settings. Results has compact Hide/Show SMA plus Change
  parameters. Fixed Back bars on settings/full crossovers retain scroll access.
- Inline crossovers: first 5 ascending rows, then 15/25/35, followed by Show all
  only if rows remain. Short lists clamp to their actual count. New optimization
  resets five rows; returning/saving/hiding preserves pagination and chart state.
- Saved lines use a partially covering animated lower sheet. New saves open it;
  bottom-left menu toggles it and changes to a down icon while open. A downward
  handle swipe or dimmed-area tap dismisses it. Bottom-right gear opens settings.
  The sheet is modal above the persistent bottom navigation, with its own scroll.
- 67 unit tests pass; 26 real Kivy UI groups pass across five portrait sizes,
  including real parameter/back/menu/gear/handle clicks, full/short crossover
  tables and preservation of prior chart, storage and notification behavior.
- `navigation.py` contains the sheet; screenshots of all screens are linked in
  `docs/UI_PREVIEW.md`. No dependency, schema, mock-data, mathematical or sender
  changes at that stage. Android/Gmail integration is now authorized and added;
  successful native compilation/device testing and Google consent remain pending.

## Stop point

Latest user direction now authorizes Android test packaging and Gmail delivery.
Implemented Buildozer 1.6.0 / p4a v2026.05.09 / NDK 28c / API35 ARM64 config,
with Google play-services-auth now pinned to 21.4.0 for its revocation API,
manual GitHub APK workflow with debug signing SHA-1 artifact, native Google
Identity Java bridge, send-only Gmail MIME/HTTPS transport and configurable
GMAIL_SENDER_ADDRESS="kelwong98@gmail.com". Tokens remain in memory, with consent
managed by Google Play services; no sender credentials or account connection
were obtained here. Connect/test-send/explicit EOD send/disconnect are wired.
Native notification permission continues after callback; channel/global disabled
checks, monochrome icon and tap intent are included. No live market data, remote
push server or background EOD scheduler added.
67 unit tests and 26 real Kivy UI groups pass (fake native/Google/HTTP). Native
Gradle packaging, physical phone permission/consent and real sending are
unverified. The first local build attempt reached checks but failed: javac
executable missing; SDK/NDK absent, Google downloads initially blocked. The
later supplied GitHub log reached Java compilation and failed on the old Google
auth 21.3.0 pin. A targeted native check with real API 35/Google classes reproduces
its three missing-symbol errors with 21.3.0 and passes with the fixed 21.4.0.
It invokes the installed JDK's compiler module through java, without a javac
launcher; the full local SDK/NDK toolchain remains unavailable. No APK produced.
GitHub CLI cannot dispatch
the workflow with current authentication; Git pushes work. User must run the
manual workflow, then follow docs/ANDROID_APK_GUIDE.md for install and Google
Cloud Android OAuth registration using that APK's SHA-1/package. Validation
record is docs/ANDROID_TEST_STATUS.md. No more approval is needed for this
already requested Android/Gmail implementation; actual account consent must be
given by the user through Google, not through chat.

History icon selection: the user chose option A from
`docs/HISTORY_ICON_OPTIONS.md`. Its native canvas implementation uses an open
circular return arrow, rounded strokes and clock hands, sized 22 dp in the
existing 44 dp button. The last-ten-history popup behavior is unchanged.

Latest visual correction: compact mockup controls are now implemented, rather
than retaining the original stacked form. Four columns at widths >=760 dp,
two columns below; Optimal SMA value/actions share a row at >=620 dp. Header
copy, spacing, responsive font sizes, rounded outlined controls with arrows,
chart axes/grid, centered legend and compact completed-state feedback follow
the approved reference. Loading, custom entry, errors, saved lines, and all
math/zoom behavior remain functional. No new dependencies or database changes.
The smoke runner verifies five portrait sizes, control placement/touch sizes,
and real window clicks on each top dropdown's arrow, plus all prior checks.
`docs/ui-current.png` and `docs/ui-phone.png` show the running application.
Mockup calendar dates and illustrative prices/results remain replaced by honest
simulated session numbers and calculated statistics. Cross-platform font
rendering can vary; no physical Android or Mac UI validation was done here.

The mock-only prototype and requested range zoom are complete. Wait for user approval before
live data-provider integration or background scheduling. Android test packaging
is now authorized; a successful build and physical-device test remain pending.
Recommended next work: compare pasted article text if supplied, agree EOD data
and adjustment rules, add fixture-backed local caching, then validate an Android
development build with portrait orientation and device lifecycle tests.


## 0.3.0 — chart inspection and investment comparison

- Results saved sheet now lists the full library across counters/scenarios;
  titles open exact saved parameters, while plot overlays remain dataset-scoped.
- One-finger EOD inspection replaces drag-to-zoom. The tooltip uses stable,
  explicitly synthetic weekday dates and full-history selected SMA values.
  Two-finger spread/contract performs continuous midpoint-anchored zoom; quick
  views and Zoom out remain independent of statistics and backtest periods.
- Section 03 compares equal-budget $100 close-to-final investments at crossings,
  fixed-seed random sessions and ranked daily percentage changes, for rolling
  1Y/3Y/5Y/Max/custom periods. It reports buys and ending values (no separate contribution figure),
  with b/c percentage differences relative to a beside their ending values,
  and discloses warm-up, simulated data, hindsight and in-sample SMA selection.
  Full crossing details remain accessible on their separate page.
- Gmail previously conflated all non-OK Android results with user cancellation.
  It now parses structured Google errors even with RESULT_CANCELED, checks Play
  services, and displays safe codes with actionable account/OAuth/network advice.
  The underlying phone authorization failure cannot be determined from the old
  generic message alone; a new APK and real Google account check remain required.
- User reports the preceding Android fixes pass on their device. New 0.3.0
  interactions are cloud-validated; they are not yet confirmed on a phone.


## Kivy desktop preview after 0.3.0

- Published as source on GitHub main for laptop review; no Android packaging or
  workflow dispatch for this preview.
- Geometric daily-line intersections now determine crossing markers and a's
  purchase prices; counts and EOD notification attribution remain unchanged.
- Scenario b is DCA at equal trading-period starts, including N=1. Scenario c
  selects a representative from the whole-dollar modal mean-price group among
  seeds 0–499. The footer uses the explicitly requested strict arithmetic-price
  percentile, not ending returns. See docs/DESKTOP_PREVIEW.md for exact rules.
- Reworded section 03, inline period selector, per-scenario N, circled help popups,
  removed old count/coverage/bulk explanation, retained b/c ending-value differences.
- Both saved libraries now group rows under collapsible security headings, with
  View, Hide/Show, heart and notification controls on every row. Expansion state
  survives refresh/navigation; cross-security Hide no longer changes an unrelated
  active line with the same SMA period.
- Validation: 93 unit tests; 33 full UI groups plus 5 focused preview groups pass.
- A Mac desktop launcher and portable source ZIP support laptop review. No native
  laptop or new Android-device verification has been performed here.

- START_HERE_MAC.md now follows the current desktop UI and the tested launcher,
  with GitHub Code/Download ZIP steps and instructions for preserving per-folder
  preview saves between downloads. The desktop guide also uses GitHub downloads.


## 0.4.0 — phone-only notifications and APK release

- Removed email toggles from every saved-SMA row, Settings email rules/recipient,
  Gmail connect/disconnect/test actions, and the app's Gmail authorization/send
  paths. Existing database columns and old values are retained for upgrades;
  preview and delivery accept phone alerts only.
- Phone Buy/Monitor controls, permission prompts and successful-delivery dedup
  remain. Permission denial clears busy controls without dispatching.
- Updated UI checks cover absence of email controls and suppression of legacy
  enabled email flags and alert objects. Updated the current guides accordingly.
- Version is 0.4.0. Added an intentional `apk-v*` tag trigger to the existing APK
  workflow because direct Actions API access is forbidden in this environment.
  Signing cache/secret preservation and manual dispatch remain available.

- Release validation: 93 unit tests and 38 full Kivy UI groups passed. Exported
  Settings/saved-menu screenshots were inspected: only phone controls remain.
  Workflow YAML and tag trigger were parsed and checked; no manual signing
  migration is requested for the release tag.


## 0.5.0 — explicit security search, desktop and APK

- Replaced the counter dropdown with a submit-only ticker/company search and a
  selected-security button. Enter and Submit share one request path. Blank input,
  typing, focus changes and results rendering make no search requests.
- Added local logo/ticker/name/exchange result rows, with initials fallback and
  no logo network requests. Included verified Simple Icons PNG assets/credits.
- Selecting a match asynchronously requests history through the preview provider.
  Search alone never loads a security. Duplicate in-flight submits are ignored;
  query edits and newer selections invalidate stale search/history responses.
  Failed loads retain the existing dataset; states are visibly retryable.
- User confirmed this is pre-integration preview mode: no Twelve Data requests
  or API key, a local 12-security catalogue and deterministic simulated history.
  Preserved the original demo fixtures and saved-line/notification behavior.
- Added pure search/provider/model checks and five running-widget search groups,
  including actual clicks, out-of-order responses and mobile keyboard geometry.
  Version 0.5.0 uses the existing APK release-tag trigger and signing identity.

- Validation: 100 unit tests and 43 full Kivy UI groups pass. The full sequence
  exposed lingering Parameters-page scroll momentum after navigation/resizing;
  returning to Parameters now stops it before restoring the top. The search test
  deliberately injects high residual velocity and verifies real Submit taps.
- Inspected search layouts at 320, 440 and 960 pixels; packaged PNG integrity,
  dependencies and Android logo/version configuration checked. No live Twelve
  Data response or physical-device result is claimed.
