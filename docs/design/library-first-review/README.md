# Library first — revised full-app review

**3 November 2026 (Singapore).** This is the selected direction with the requested
changes, covering the entire application. The images come from the running,
unreleased Kivy desktop implementation. **Only design/review files are uploaded
in this change.** The published application source remains version 0.6.0; no
version bump, release tag or APK build is requested by this upload.

## Open the maps directly on GitHub

These PNGs preview in GitHub; no ChatGPT file viewer or web preview is required.

- **[Complete app navigation map](full-app-flow.png)** — launch decision, all
  screens, actions, return paths, settings, archive and comparison branches.
- **[01 — Start and learn](01-start-and-learn.png)** — empty library, the guide,
  submitted search and parameters.
- **[02 — Analyze and compare](02-analyze-and-compare.png)** — Results, backtest,
  explanatory popup and crossing details.
- **[03 — Save and return](03-save-and-return.png)** — populated library, saved
  controls, archive/restore and phone Settings.

Each board also has an SVG of the same name for sharp zooming/export. The
[whole-app reviewer](whole-app-review.html) is a self-contained HTML file with
captured-screen navigation and the full map. GitHub displays HTML as source:
download it and open it locally if you want to click through it. The PNG links
above are the primary review route and require no download.

## Your requested changes

1. Empty Library starts with **“New to moving averages and upward crossing buy
   signals?”** and a guided-example action, replacing “Your first line starts
   here.” New analysis follows the sample card.
2. The Home / Saved / Learn bottom bar is removed. The native preview uses fixed
   top controls and Back navigation. Results keeps Library, Saved SMAs and
   Settings accessible above the chart and saved overlay.
3. App launch always opens Library. With at least one saved SMA, it is the
   **populated page 05**; without any saves, it is **empty page 01**. Removing
   the final save changes the library to empty. Restoring a line changes it
   back to populated. A reopened app reads these states from SQLite.
4. Parameters uses **Custom** for the expandable fictional-pattern settings,
   rather than Advanced options. Preset and custom frequency entry remain.
5. The isolated guided example uses **three simulated years (756 sessions)**,
   several crossing frequencies, the real optimizer and real investment
   comparison calculations. It explains possible recovery signals as well as
   false signals, SMA lag and losses after buying. It does not change the user's
   selection or save any example line.
6. The pending chart-heading fix is included locally: **company logo, then
   company name**, with whole-word ellipses and the existing initials fallback.
   Exchange/ticker strings are removed from the chart heading.

## Complete app behavior covered

- Library → optional Guide, New analysis or exact saved-line View. Saved rows
  keep their heart, View, Hide/Show and phone notification controls.
- Search only on Enter/Submit → choose a logo/ticker/name match → simulated
  history → Parameters. Empty/error responses retain the existing analysis
  and allow retry. Twelve Data integration remains pending.
- Parameters/Custom → worker calculation → Results. Validation stays on the
  form; conflicting controls are disabled during history/calculation work.
- Results → EOD/date/SMA inspection, two-finger pinch, quick period ranges,
  Save/Unsave, saved sheet, Change parameters or Settings.
- Backtest → 1Y/3Y/5Y/Max/custom years, equal buy counts, only ending values,
  b/c percentage differences versus a, information help and all crossings.
  Existing comparison rules are preserved: interpolated crossing fills, DCA
  interval starts and the most common whole-dollar mean-price group among
  500 random samples.
- Recently unsaved → last ten configurations → exact restoration including
  original visibility and phone flags. Archive identities use smaller logos.
- Settings → phone buy/monitor rules, EOD preview/delivery and permission test.
  Allow/deny states remain explicit; email controls stay removed.
- Back dismisses help, archive, keyboard and saved sheet first, then returns
  through the page stack. Saved View from Library returns directly to Library;
  analyzing from Parameters returns along Parameters/Search/Library.

## Guided-example wording and calculations

An upward SMA crossing **may suggest** that price is starting to recover.
Waiting for a crossing can filter out some buys while the price is below its
average. It **does not guarantee recovery or stop a subsequent price fall**:
SMAs lag, and a false crossing can precede another decline. The generated lesson
contains both recoveries and subsequent falls; it is not selected to show only
successful signals. The optimizer matches crossing frequency, not returns.

For each chosen frequency, the guide shows $100-per-buy ending values for
crossing, equal-period and modal random scenarios. All have the same theoretical
buy count and use the same existing comparison engine as Results. Full example
inputs, SMA samples, marker positions and ending values are recorded in
[guide-calculations.json](guide-calculations.json). These are fictional prices,
not observations of any real company or a forecast.

## Individual screens

| View | Full-resolution capture |
| --- | --- |
| 01 Empty Library | [Open](screens/empty.png) |
| 02 Search matches | [Open](screens/search.png) |
| 03 Parameters | [Open](screens/parameters.png) |
| 03a Custom expanded | [Open](screens/custom.png) |
| 04 Results / company heading | [Open](screens/results.png) |
| 05 Populated Library | [Open](screens/populated.png) |
| 06 Guide | [Viewport](screens/guide.png) · [entire scroll content](screens/guide-full.png) |
| 07 Saved SMA sheet | [Open](screens/saved-sheet.png) |
| 08 Backtesting | [Open](screens/backtest.png) |
| 08a Random explanation | [Open](screens/help.png) |
| 09 Settings | [Open](screens/settings.png) |
| 10 Unsaved archive | [Open](screens/archive.png) |
| 11 Crossing details | [Open](screens/crossovers.png) |

## Validation and release boundary

The local unreleased implementation passed **102 unit tests**, **46 existing
running-widget regression groups**, and **6 dedicated library-flow groups**.
The latter cover empty/populated startup, a reopened store, isolated guide
calculations, submitted selection, Custom, chart identity, saved View/Back,
last-line unsave, archive restoration and 320/440/960px layouts. A further check
confirms that leaving search or parameters cancels pending work so a late
completion cannot unexpectedly change the page or selected dataset. The three-year
sample is checked for both rises and falls following crossing prices.

These are cloud desktop checks of shared widgets; physical Android execution
is not claimed. Version 0.6.0, package identity and APK signing settings are
unchanged. The application edits and updated native tests are kept local for a
later UI release; this GitHub proposal commit contains review assets and their
generator, not those application changes.

The boards and self-contained review HTML can be regenerated from the stored
captures using `python -m scripts.render_library_review`. PNG rendering uses
CairoSVG as a design tool; no application dependency was added.
