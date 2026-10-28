# Prototype handoff

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
- 53 standard-library tests passed; 22 running Kivy smoke groups passed.
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
- No dates/calendar, adjustments, panning, pinch zoom, live data, scheduling, or APK packaging.
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
- 53 unit tests and 22 running Kivy smoke groups passed in the current version,
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
  and email stays preview-only, explicitly selected by the user. No SMTP or
  network sender, provider account, domain, API, scheduler, backend or APK added.
- Manual session preview / Android test / enabled-EOD delivery buttons. Persistent
  successful-send deduplication, failure retry and clear desktop limitation.
  There is no automatic/background EOD arrival source or remote push service.
- 53 unit tests and 22 running UI groups pass, including real window clicks on
  the heart/history/switches, fake Android delivery and duplicate suppression,
  actual subject/body text, migration, ten-entry pruning, restore and five sizes.
- `docs/NOTIFICATIONS.md` explains novice testing, exact templates, limitations
  and future device permissions. Settings and saved-line screenshots are linked
  from the GitHub preview page. Physical Android delivery remains unverified.

## Stop point

Latest user direction: complete Android notification implementation/integration
and physical-device testing when building the Android app later. The existing
adapter is preparatory and unverified on-device; current desktop behavior stays
manual previews/testing. Do not start Android packaging or background work now.
Email remains preview-only. Expected future volume is at most about 50 messages
per month. Resend is a proposed custom-domain sender, not an approved or
configured provider; current free-plan terms need confirmation before setup.

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
data-provider integration, background scheduling, or Android APK packaging.
Recommended next work: compare pasted article text if supplied, agree EOD data
and adjustment rules, add fixture-backed local caching, then validate an Android
development build with portrait orientation and device lifecycle tests.
