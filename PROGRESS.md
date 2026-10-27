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

## Stop point

The mock-only prototype and requested range zoom are complete. Wait for user approval before
data-provider integration, background scheduling, or Android APK packaging.
Recommended next work: compare pasted article text if supplied, agree EOD data
and adjustment rules, add fixture-backed local caching, then validate an Android
development build with portrait orientation and device lifecycle tests.
