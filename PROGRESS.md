# Prototype handoff

## Completed

- Pure, Kivy-independent SMA engine, documented upward-crossing/equality/gap
  rules, whole-history annual targets, and shorter-period tie-break.
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
- 21 standard-library tests passed; 13 running Kivy smoke groups passed.
  Screenshots generated in ignored `artifacts/`. No failed or skipped checks.

## Decisions to preserve

- All data and series labels explicitly say simulated; no live services.
- Target = frequency × total session count / 252, including warm-up/gaps.
- Search periods 2..history length-1 using each period's own valid history.
- Equality carries the previous strict side; gaps reset it; first side is baseline.
- Active-period visibility takes precedence when that period is also saved.
- Zoom only changes the view, preserving full-history SMA warm-up, crossing
  statistics, and table rows. Visible markers are filtered to the selected range.
- Inclusive zoom endpoints round outward to session indices. Drags under 6 dp
  are ignored. New counter/scenario resets zoom; overlay changes preserve it.
- Calculation changes belong in engine/model tests before UI changes.
- Each cloud task is already isolated: use the existing checkout; do not create
  a Git worktree unless explicitly requested.

## Known limitations / remaining work

- LinkedIn source returned HTTP 403; implementation follows the supplied prompt.
- Desktop UI rendered and exercised through SDL offscreen/Mesa, not a physical
  Android device. Clipboard cutbuffer warnings in this headless environment are
  nonfatal; no clipboard integration was verified.
- Long SMA warm-up can favor rare crossings; no profitability inference.
- No dates/calendar, adjustments, panning, pinch zoom, live data, scheduling, or APK packaging.
- Active result/dropdown selections reset on restart; saved lines persist.
- Future genuine histories need performance profiling and schema migrations.

## Frequency proposal: tested separately, not activated

- `experiments/observable_frequency.py` tests the proposed usable-comparison
  annualization and cap: min(floor(H/2), 252) through 756 sessions, then H-504.
- Usable exposure excludes the initial SMA baseline, gaps, and re-warm-up.
  Candidates must actually satisfy the minimum coverage promised by the cap;
  missing data can produce a helpful insufficient-history error.
- Annual-frequency error determines the winner; exact rational ties select the
  shorter period. No application code imports the experimental module.
- All 36 unit tests passed: 21 existing checks and 15 new proposal checks.
- Evaluated all six current 252-session series at targets 12, 6, and 1. Longer
  series were generated only as isolated boundary fixtures, not as UI data.
- Main result: DEMO-SGX Sideways target 12 selects SMA 22, 33 crossings over 230
  comparisons, 36.1565/year. DEMO-SGX Oscillating selects SMA 42, exactly 12/year.
- Normalization alone, without a coverage rule, can select SMA 251 with zero
  events and just one comparison. The complete proposed policy rejects that
  short-exposure result. Several simulated targets remain unattainable.
- See `docs/observable-frequency-evaluation.md` and reproduce with
  `python -m experiments.evaluate_frequency` (no Kivy required).
- Remaining: a separate application integration step. The optimizer, UI
  frequency, saved-line behavior, settings,
  mock generator, 252-session default, and active SMA limits remain unchanged.

## Recorded summary for later printing

- `APP_SUMMARY.md` records the calculation and crossing definitions, agreed
  experimental cap/coverage/frequency rules, single-average display requirement,
  unreachable-target and short-history limitations, evidence, zoom/persistence
  behavior, and current prototype constraints.
- It explicitly separates active app behavior from the tested proposal so a
  printed summary does not imply that the policy or longer mock data is active.
- The README and evaluation report link to this summary. Saving these records
  does not activate the experimental policy or change application defaults.

## Stop point

The mock-only prototype and requested range zoom are complete. Wait for user approval before
data-provider integration, background scheduling, or Android APK packaging.
Recommended next work: compare pasted article text if supplied, agree EOD data
and adjustment rules, add fixture-backed local caching, then validate an Android
development build with portrait orientation and device lifecycle tests.
