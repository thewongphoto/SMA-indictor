# Prototype handoff

## Completed

- Pure SMA engine with documented crossing/equality/gap rules, adjusted annual
  targets over observable history, automatic cap and shorter-period tie-break.
- Fixed-seed 252-session generators for two fictional counters × three scenarios.
- Native Kivy canvas price/SMA overlays and triangles at calculated event indices.
- Preset/custom target controls, background calculation/loading state, summary
  cards, full selected-result crossover table, and helpful invalid/empty states.
- SQLite saved lines, per-counter/scenario scoping, duplicate protection,
  multiple overlays, persistent saved visibility, and removal.
- Responsive portrait column, vertical scrolling, and beginner run instructions.
- Drag-to-zoom in either direction, immediate green start/red end boundaries,
  translucent selection, auto-scaled visible y-range, and a top-right Zoom out
  button that appears only while zoomed. Touches in the plot bypass scroll delay;
  page swipes outside the plot and mouse-wheel scrolling remain available.
- 39 standard-library tests passed; 14 running Kivy smoke groups passed.
  Screenshots generated in ignored `artifacts/`. No failed or skipped checks.

## Decisions to preserve

- Mock data only; 252-session defaults and dataset version remain unchanged.
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
- 39 unit tests and 14 running Kivy smoke groups passed after integration,
  including the active Sideways result: SMA 22, 33 crossings / 230 comparisons,
  36.16/year. Scenario, target, zoom, save/load and error checks passed.
- `APP_SUMMARY.md`, README and Mac instructions now describe active behavior.
  The evaluation report is retained as a historical pre-integration record.
- Mock generator, 252-session length and SQLite schema/version are unchanged.
  Existing saved periods are preserved; those above the cap are labelled as
  outside the current search limit.
- Remaining: longer default mock data, genuine data, Android device validation
  and packaging are separate subsequent tasks.

## Stop point

The mock-only prototype and requested range zoom are complete. Wait for user approval before
data-provider integration, background scheduling, or Android APK packaging.
Recommended next work: compare pasted article text if supplied, agree EOD data
and adjustment rules, add fixture-backed local caching, then validate an Android
development build with portrait orientation and device lifecycle tests.
