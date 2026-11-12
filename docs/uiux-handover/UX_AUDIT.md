# UX/UI audit — SMA Stock Analyzer (repo main)

Scope: the Kivy portrait app in `sma_analyzer/`. Findings come from reading the source; none were tested on a device yet. Severity: H = blocks or confuses a core task, M = slows it, L = polish.

## Onboarding and first run
1. **H — New users land on an empty library with no explanation of the first step.** The "What is an SMA?" intro is a card under the library header, and the guided example is a secondary button (`app.py`, `library_intro`). Make the guided example the first action for a new user.
2. **H — Jargon before value.** "Target upward crossings/year", "observed", "SMA (X days)" and "EOD monitor" appear before the user has a reason to care. Lead with the outcome ("About 4 buy signals a year") and move the definition behind a tap.
3. **M — The disclaimer is long and repeated.** The research-tool note at the bottom of Results runs to three sentences of fine print. Keep one short line on screen and link the rest.

## Navigation and information architecture
4. **H — Four levels to reach a result.** Library → Search → Set preference → Results, plus a Saved SMAs bottom sheet that behaves differently from the library. Collapse search and preference into one screen with a visible step indicator.
5. **M — Settings is reached two ways.** A gear icon sits on every page heading and another in the Results footer. Keep one entry point, in a labelled tab bar.
6. **M — Results has two competing lists.** The saved sheet and the library both hold saved SMAs. Use one list.

## Controls and labels
7. **H — Icon-only controls with unclear meaning.** The heart saves, the palette sets colour, the pencil renames, the gear opens settings, and the chevron goes back. None has a text label. Pair each icon with a word, or use text buttons.
8. **H — No on-screen cancel during optimisation.** The overlay only says "Optimizing SMA…"; cancelling depends on the Android Back gesture or Escape. Add a visible Cancel button to the overlay.
9. **M — Custom target is hidden behind "Custom +".** Users who need a non-standard frequency must discover the toggle. Show the segmented choices with Custom as the last option.
10. **M — Search only runs on Enter or Submit.** Typing shows no results, and the hint is 11sp grey text. Say "Search" on the button and state the action in the field's placeholder.
11. **L — "Hide SMA" and "Save" sit next to each other with different meanings.** Use "Save to library" and "Hide from chart", with a short confirmation.

## Gestures and discoverability
12. **M — Key chart actions are gesture-only.** Pinch zoom, one-finger inspection and the swipe handle on sheets are not shown anywhere. Add a one-line hint on first use, and keep the Zoom out button.
13. **L — Sheet dismissal relies on a 32dp handle.** Add a visible close control in the sheet heading.

## Readability and visual system
14. **M — Small secondary type.** Field labels are 10sp, captions 10–11sp, and the "Change parameters" button drops to 11sp on phones. Use at least 12sp for labels and 14sp for body on narrow screens.
15. **L — Every panel looks the same.** Search, controls, optimal result, chart and cards all use one surface, so nothing signals priority. Reserve the filled surface for the primary result and use hairline dividers elsewhere.
16. **Pass — Contrast.** Muted text (#94A8BF) on the navy panel (#1F3048) measures about 5.5:1, above the 4.5:1 body-text minimum. Keep this when restyling.

## Recommended order
1. Items 1, 4, 7, 8 (first-run path, shorter flow, labelled controls, visible cancel).
2. Items 2, 9, 10 (plain-language copy and visible inputs).
3. Items 5, 6, 12, 14 (navigation consolidation, gesture hints, type sizes).
4. Visual pass in Claude Design once the structure is settled.
