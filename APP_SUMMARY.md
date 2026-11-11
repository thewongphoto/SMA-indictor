# SMA Stock Analyzer — app summary and calculation conditions

**Current Android release: 0.13.3.** Fixes chart startup for preview datasets
without quote-currency metadata. Live data keeps its real currency. Native
iOS releases are paused at the user's request; the planned iPhone route is
Vercel. See the [release notes](docs/RELEASE_0_13_3.md).

**Included from 0.13.2:** Chart dollar/percentage changes compare the first
and last visible adjusted closes, following presets and pinch zoom without
network calls. The corrected logo shows the turquoise price rising through
the orange SMA; launcher/launch-screen branding and the animated calculation
overlay use it. This release also fixes cross-platform PNG comparison in the
iPhone workflow: regenerated pixels must match, while compression can differ.
See the [release notes](docs/RELEASE_0_13_2.md).

**Included from 0.13.1:** The app uses real dividend/split-adjusted daily
history, persistent caches, saved names/colours and native Android daily checks.
This release applies the selected Crosspoint app icon, uses actual 365-day
calendar exposure for live annual-frequency matching, and fixes the iPhone
signing-kit background-identifier verifier. Saved SMA periods and notification
preferences are preserved. X/year is a closest historical average, not a quota
guaranteed in every individual year. See the
[release notes](docs/RELEASE_0_13_1.md),
[Android guide](docs/YAHOO_ANDROID_TESTING.md) and
[Vercel/iPhone web-app guide](docs/PRIVATE_IPHONE_INSTALLATION.md).
Apple signing and physical-device iPhone behavior still require validation.

The older development records below describe the original **simulation** and
its calculation policy; statements about mock-only prices, missing schedulers
or Gmail refer to those historical revisions, not the current live app.

**Android 0.8.0 update:** real Yahoo search/daily history, persistent caches and
copyable HTTP/app/cache diagnostics are included in the private data test.
See [the Android guide](docs/YAHOO_ANDROID_TESTING.md). Background fetching,
notification delivery and iOS signing remain separate future validation.

**Desktop update, 5 November 2026:** the main branch adds private Yahoo EOD
retrieval, persistent prices/searches, actual dates/currency and full-history
MAX. Follow [Yahoo desktop testing](docs/YAHOO_DESKTOP_TESTING.md).
The 0.7.0 APK and the simulation rules recorded below remain separate;
background fetching and notification delivery testing are deferred.

**Historical preview release: 0.7.0.** The approved library-first UI, three-year guide,
Parameters/Custom and logo/name chart heading are documented in the
[release notes](docs/RELEASE_0_7_0.md). The current app is phone-notification-only;
the Gmail/authorization sections below describe older development work and do
not require account setup for this release. Prices remain simulated.

This document records the app's purpose, inner workings, limitations, and the
active frequency policy for a future printed summary. The tested policy is now
connected to the running app; the status table records the remaining scope.

## Historical implementation status (0.7.0)

| Component | Status |
| --- | --- |
| Mock-only desktop Kivy app, chart, saved lines, crossover table, range zoom | Implemented |
| Six fictional datasets, each with 1,260 sessions (five years) | Active in the app |
| Original frequency calculation and unrestricted candidate range | Replaced by the agreed observable-history policy |
| Warm-up-adjusted frequency and automatic history-dependent SMA cap below | Active in `sma_analyzer/engine.py` and `policy.py`; checked against the research reference |
| Default chart view and available presets | 1Y on startup/new data; 3Y and 5Y only when available; Max shows all history |
| Live market data / background EOD scheduler | Not implemented |
| Debug Android APK configuration/workflow | 0.7.0 tag-triggered workflow runs unit, full UI and library-flow checks before packaging; inspect the GitHub run for build completion |
| Saved hearts, ten-entry unsave history, channel/type settings and EOD previews | Implemented and tested |
| Android local notifications | Generic phone notification passed per user report; 0.7.0 physical UI validation remains pending |
| Gmail sending | Removed from the active application in 0.4.0; older standalone modules retained as legacy code |

Download the updated repository to use the new calculations. Files already
downloaded to a Mac do not update automatically when GitHub changes.

## Purpose and inputs

The app searches for an integer simple moving average (SMA) period whose
historical upward-crossing frequency is closest to a selected target. The
presets are 12, 6, and 1 crossings per trading year. Manual entry accepts other
positive integers that fit a signed 64-bit SQLite integer.

All data is simulated. DEMO-SGX and DEMO-US are fictional counters, not actual
securities, currencies, or exchange feeds. Each has Trending, Oscillating, and
Sideways scenarios generated with fixed random seeds. The current app creates
1,260 closing prices (five trading years) per counter/scenario combination, identical between runs.
Prices use fictional units; chart labels identify simulated data explicitly.

One trading year is defined as **252 trading sessions**. This is a convention
for annualization, not a calendar or an exchange-specific holiday schedule.
Chart session labels are observation numbers, not dates. Nothing connects to
live market APIs or requires a backend for analysis. Optional Gmail sending
uses the internet and Google send-only authorization; no financial credentials
are requested.

## SMA arithmetic and upward-crossing definition

For period N, each daily SMA is the arithmetic average of that session's close
and the preceding N-1 closes. It requires N consecutive finite prices.

- An SMA of N sessions has N-1 initial warm-up sessions without an SMA value.
- The first SMA appears on session N. It establishes the price's starting side
  relative to the SMA; it does not count as a crossover.
- The earliest possible upward crossing is on session N+1.
- A crossing means a transition from strictly below the SMA to strictly above it.
  Downward crossings do not count.
- Equality keeps the last strictly above/below side. Below → equal → above
  counts once; above → equal → above does not. Initial equality establishes
  neither side. Equal observations are still observable time.
- Missing prices, NaN, or infinity invalidate the relevant SMA windows and
  restart warm-up. A missing price or SMA resets the crossing baseline; no
  crossing is inferred across that gap.
- Computation uses unrounded values and strict comparisons, with no hidden
  tolerance. Display rounding does not determine whether a crossing occurred.

Period 1 is supported by the arithmetic function but excluded from optimization
because the SMA would always equal the price. Candidate optimization begins
at period 2.

## Recorded policy: annual frequency over all observable history

The intended objective is to use **all available observable crossing history**,
not just the latest 252 sessions. It is not changed by the chart's zoom range.

Define:

- H: total input trading sessions.
- N: the candidate SMA period.
- C: upward crossings over that candidate's entire observable history.
- E: usable session-to-session comparisons for that candidate.

With complete data, **E = H-N**. There are H-N+1 valid SMA observations, but
the first is a baseline; only the following H-N comparisons can reveal a
crossing. With missing data, E is counted directly from adjacent observations
where both price and SMA are finite. Gaps and re-warm-up are excluded.

```text
Observable years = E / 252
Annual crossing frequency = C × 252 / E
Candidate error = absolute difference between annual frequency and target
```

The candidate with the smallest annual-frequency error wins. Comparing raw
crossing-count errors is insufficient because candidates have different usable
durations. Equal annual-frequency errors choose the shorter SMA. The production optimizer
uses exact rational rates for this tie-break and rounds only for presentation.

For example, 36 crossings over 756 usable comparisons means 12 crossings/year.
Three years of raw prices do not necessarily contain three usable years for
an SMA: some of that input is needed to establish the SMA and its baseline.

Only this warm-up-adjusted annual frequency is displayed. There is no second,
unadjusted average. The raw crossing
count and usable history can be shown to explain the single reported rate.

## Recorded policy: automatic candidate cap and minimum coverage

The maximum candidate period is determined by history length, not by a
user-configurable setting:

```text
If H <= 756 sessions:
    cap = min(floor(H / 2), 252)

If H > 756 sessions:
    cap = H - 504

Candidate periods = every integer from 2 through cap, inclusive
Minimum observable comparisons = H - cap
```

| Available input | Maximum SMA | Minimum usable comparisons | Equivalent years |
| --- | ---: | ---: | ---: |
| 252 sessions — 1 year | 126 | 126 | 0.5 |
| 504 sessions — 2 years | 252 | 252 | 1 |
| 756 sessions — 3 years | 252 | 504 | 2 |
| 757 sessions | 253 | 504 | 2 |
| 1,008 sessions — 4 years | 504 | 504 | 2 |
| 1,260 sessions — 5 years | 756 | 504 | 2 |

This satisfies the at-most-50%-of-history cap for input of three years or less,
and avoids a sudden cap reduction when moving beyond three years. Above three
years, candidates retain at least two usable trading years. The shorter-history
exception permits less than two years; it must not be described as a universal
two-year guarantee.

Missing data can reduce actual coverage below H-cap even when the period fits
the cap. The optimizer rejects those candidates. If no candidate meets the
coverage requirement, it reports insufficient valid history rather than
inventing exposure or silently relaxing the requirement. At least four input
sessions are needed to admit period 2 under the proposed cap; that technical
minimum does not imply a statistically reliable annual frequency.

## Conditions and limitations of interpreting a result

- A target may be unattainable. Always report the closest eligible candidate's
  actual frequency and crossing count, including when the error is large.
- Different targets can select the same SMA when no other eligible candidate
  is closer. That is not automatically a calculation error.
- Annualization from a short usable history can be unstable. A minimum coverage
  rule controls duration; it does not guarantee statistical reliability.
- More history helps establish longer SMAs and measure longer periods, but does
  not guarantee the target becomes attainable or future behavior stays similar.
- Changing the average alone is insufficient: very long SMAs with almost no
  usable history can still produce misleading winners. Apply coverage and
  frequency rules together when integrating the proposal.
- The automatic cap itself grows smoothly, but the selected SMA can change
  abruptly as prices, candidates, or their ranking change.
- "Optimal" means closest among the tested integer periods, for the specified
  dataset, coverage rules, and frequency objective. It does not establish
  profitability or guarantee a future crossing frequency.

## Evidence from the isolated evaluation

For target 12/year on the current DEMO-SGX simulated data, the complete proposed
policy produces the following in both the reference evaluation and the active
app:

| Scenario | Selected SMA | Crossings | Usable comparisons | Annual frequency |
| --- | ---: | ---: | ---: | ---: |
| Trending | 11 | 61 | 1,249 | 12.3074 |
| Oscillating | 721 | 26 | 539 | 12.1558 |
| Sideways | 254 | 125 | 1,006 | 31.3121 |

In the historical 252-session sideways fixture, adjusting frequency without restricting coverage
selected SMA 251: zero crossings over only one usable comparison. The complete
policy excludes that result by requiring at least 126 usable comparisons.

Validation after application integration:

- 75 unit tests passed, including active-engine/reference agreement, coverage,
  caps, displayed model results, and preservation of earlier saved lines; none
  failed or were skipped.
- The comparison runner evaluated all six current datasets at all three preset
  targets, plus eight isolated longer-history boundary cases.
- The current Kivy UI run passed 30 check groups, including the known
  adjusted-frequency result in actual widgets, usable coverage, touch routing,
  zoom selection, reset, chart/table consistency, persistence, and errors.
- UI rendering was exercised with SDL offscreen/Mesa on Linux. No automated
  Mac GUI, physical Android, or APK validation has been performed.
- Following the first GitHub build failure, a targeted compile of the unchanged
  Gmail Java bridge reproduced the three errors with Google auth 21.3.0 and
  passed with 21.4.0 against real Android API 35/Google libraries. The build
  now pins 21.4.0. Full APK packaging and actual account/device tests remain
  pending; see [Android validation status](docs/ANDROID_TEST_STATUS.md).

See [the full evaluation report](docs/observable-frequency-evaluation.md) for
reproducible commands and all results. Passing these tests demonstrates the
specified calculations and controls, not investment performance.

## Chart, zoom, and local saving

- A full-width Optimal SMA card, including an outline/red save heart and Hide/Show SMA line,
  sits above the chart. Only two frequency cards sit below it: Target Crossing
  Frequency on the left and Actual Crossing Frequency on the right.
- The raw crossing count is part of section 03, Crossovers — Selected SMA,
  and refers to the full observable history even when the chart shows 1Y.
- The timeline dropdown is below the counter/scenario row. It always starts at
  1Y on launch/new data. 3Y is omitted below 756 sessions; 5Y below 1,260. Max
  always offers the available history. Selecting a preset shows the latest
  matching sessions, and changing a preset does not recalculate statistics.
- The rounded label/arrow share one clickable target. The current option is
  shaded. Legend entries use colored dashes and the same outlined plus marker,
  with descriptive labels and no colons or color-name prefixes.

- The chart draws simulated closing prices, visible SMA lines, and plus signs
  with a thin black border
  at calculated upward-crossing events. Saved overlays can be hidden or shown.
- The crossover table describes the selected result. Chart markers describe
  every visible SMA line; these scopes are intentionally different.
- Touch or click and hold inside the plot to select an x-range. The earlier
  boundary is always green, the later boundary red, and the selected area shaded.
  Crossing the original touch position changes the moving boundary's color.
- Release zooms to the chosen range and scales y to the visible prices and SMA
  values. Nested zoom is supported. Zoom out appears beside the title only
  while a custom selection is zoomed and restores the selected timeline.
- Selection rounds outward to bordering sessions. Movements under 6 dp do not
  zoom; release beyond the plot clamps the x-range to the visible plot.
- Zoom changes the view, not the optimization history, statistics, or table.
  New counters/scenarios reset zoom. Target/overlay changes preserve the range.
- Page swipes can start outside the plot; mouse-wheel scrolling remains available.
- Saved lines use SQLite on the local device, scoped by counter, scenario, and
  mock-data version. Period, target, and saved visibility persist. The active
  analysis and dropdown selections do not persist across restarts.
- No account or cloud synchronization is provided. Derived SMA/event values are
  recalculated; changing the dataset version will require deliberate handling
  of older saved lines in a future integration.

## Saved hearts, recovery and notifications

- Each saved SMA label has a dash matching its chart colour. Colours are stable
  when other periods are hidden; the active period remains gold.
- The Optimal SMA heart is grey/outlined when unsaved and red/filled when saved
  for that exact period and target. Tapping again unsaves it. Saved-row hearts
  also unsave; the current calculated overlay can remain visible independently.
- The history icon in section 02 opens the last ten distinct saved-then-unsaved
  configurations, newest first across counters/scenarios. Older entries are
  discarded; restore recovers period, target, visibility and channel flags.
- Per saved line, Phone/Email On/Off controls are separate from Hide/Show.
  The Settings screen holds two type switches per channel and a locally stored
  recipient address. All toggles start Off. Missing-address validation blocks
  enabling email, and clearing the address is blocked while a saved line has
  email On.
- Buy uses the existing upward-crossing engine at the selected EOD observation.
  Monitor means a strictly below-SMA close, once per simulated session; equality,
  gaps and warm-up do not invent alerts. Both channel and type must be enabled.
- The user has now authorized Android testing and Gmail delivery. Preview still
  sends nothing; native Google authorization and explicit Gmail test/EOD send
  actions are implemented. Sender defaults to kelwong98@gmail.com in settings.py,
  configurable for a later dedicated account. The user must set up the Google
  project/Android OAuth client and authorize the sender. No account was connected
  or real email sent in this session. Expected volume remains about 50/month.
- A lazy Android local-notification adapter and manual test controls are present.
  Desktop Kivy integration checks inject a fake sender. Physical OS delivery,
  permission prompts, sounds and background behavior have not been verified.
  No APK was produced; local compilation was blocked. No scheduler was added.
  Local notification delivery while running is
  distinct from remote push delivery or reliable closed-app monitoring.
- Successful EOD sends are deduplicated persistently by data version, channel,
  type, counter, scenario, period, target and session. Failures remain retryable;
  a crash between posting and recording can still cause a repeat.
- The SQLite migration is additive and preserves older saved lines. Email,
  settings, history and delivery records remain on the device. No shared sending
  secrets are stored. See [notification testing](docs/NOTIFICATIONS.md).

## Screen structure

- Screen 1 contains the heading, parameters and an all-counter/scenario library
  of saved SMAs, and is the launch screen. Library actions say View; the title
  is also clickable. View opens the exact saved period/target without rerunning
  optimization, reveals its selected overlay and shows a Saved SMA caption.
  Successful optimization navigates to Screen 2. Change parameters returns to 1
  with the controls retained; failed/invalid calculations remain on 1.
- Screen 2 contains Optimal SMA, chart, two frequency cards and coverage. The
  Hide/Show SMA control is narrower, alongside the heart and Change parameters.
- Inline Screen 2a is below these results. It shows the first five events in
  ascending session order; each arrow adds up to ten, through 35. Show all
  appears only when there are more than 35, and opens a complete event screen
  with a fixed Back arrow. Short lists end cleanly. A new result resets to five.
- Screen 2b is a modal partial bottom sheet for saved lines. New saves open it;
  the fixed bottom-left menu toggles it. A downward handle swipe or outside tap
  also closes it. The list scrolls independently; bottom navigation stays usable.
- A fixed bottom-right gear opens Screen 3 / notification settings. A fixed Back
  arrow returns to Results. Full-list and settings Back controls remain available
  while scrolling. Page navigation retains chart range/result/scroll state.
- The native Kivy ScreenManager and animated sheet add no dependency and do not
  change the calculation, storage or alert rules. Physical Android validation
  and Google consent/real delivery remain to be verified.

## Current app behavior and remaining work

The optimizer now searches under the agreed automatic cap, requires actual
usable coverage, and ranks candidates by warm-up-adjusted annual-frequency
error. The cards, explanation, chart, and table use this active result. Historical
saved lines remain viewable; those outside today's cap are labelled, not deleted
or treated as newly optimized results.

The app uses Python and Kivy's native canvas, with SQLite local persistence.
The approved mockup guides its header, rounded outlined dropdowns, compact
controls, Optimal SMA strip, chart grid/axes and centered symbol legend. Wider
portrait windows use four control columns (>=760 dp) and place the Optimal SMA
value beside its actions (>=620 dp); narrow phones use two columns and actions
below the value. Five portrait sizes, including 320 pixels wide, were exercised.
It is portrait-first with vertical scrolling; panning, pinch zoom, calendar
dates, exchange calendars, corporate-action adjustments, and return/backtest
analysis are not implemented. Kivy and certifi are the direct desktop dependencies. Android adds native Google
Identity/Pyjnius through its build configuration.

The supplied LinkedIn article returned HTTP 403 and could not be read; the
implementation follows the written requirements and the recorded decisions.
Long genuine histories will need performance profiling and schema planning.

Genuine market data,
background scheduling remain future work. Android debug packaging is now
authorized and configured, but awaits a successful native build and device test.
See docs/ANDROID_APK_GUIDE.md and docs/ANDROID_TEST_STATUS.md.
