# SMA Stock Analyzer — app summary and calculation conditions

This document records the app's purpose, inner workings, limitations, and the
active frequency policy for a future printed summary. The tested policy is now
connected to the running app; the status table records the remaining scope.

## Implementation status

| Component | Status |
| --- | --- |
| Mock-only desktop Kivy app, chart, saved lines, crossover table, range zoom | Implemented |
| Six fictional datasets, each with 252 sessions | Active in the app |
| Original frequency calculation and unrestricted candidate range | Replaced by the agreed observable-history policy |
| Warm-up-adjusted frequency and automatic history-dependent SMA cap below | Active in `sma_analyzer/engine.py` and `policy.py`; checked against the research reference |
| Longer histories | Used only as isolated test fixtures; app defaults remain unchanged |
| Live market data, background scheduling, Android APK packaging | Not implemented |

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
252 closing prices per counter/scenario combination, identical between runs.
Prices use fictional units; chart labels identify simulated data explicitly.

One trading year is defined as **252 trading sessions**. This is a convention
for annualization, not a calendar or an exchange-specific holiday schedule.
Chart session labels are observation numbers, not dates. Nothing connects to
live APIs, sends email, requests financial credentials, or requires a backend.

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
| Trending | 11 | 13 | 241 | 13.5934 |
| Oscillating | 42 | 10 | 210 | 12.0000 |
| Sideways | 22 | 33 | 230 | 36.1565 |

For the sideways example, adjusting frequency without restricting coverage
selected SMA 251: zero crossings over only one usable comparison. The complete
policy excludes that result by requiring at least 126 usable comparisons.

Validation after application integration:

- 39 unit tests passed, including active-engine/reference agreement, coverage,
  caps, displayed model results, and preservation of earlier saved lines; none
  failed or were skipped.
- The comparison runner evaluated all six current datasets at all three preset
  targets, plus eight isolated longer-history boundary cases.
- The integrated Kivy UI run passed 14 check groups, including the known
  adjusted-frequency result in actual widgets, usable coverage, touch routing,
  zoom selection, reset, chart/table consistency, persistence, and errors.
- UI rendering was exercised with SDL offscreen/Mesa on Linux. No automated
  Mac GUI, physical Android, or APK validation has been performed.

See [the full evaluation report](docs/observable-frequency-evaluation.md) for
reproducible commands and all results. Passing these tests demonstrates the
specified calculations and controls, not investment performance.

## Chart, zoom, and local saving

- The chart draws simulated closing prices, visible SMA lines, and triangles
  at calculated upward-crossing events. Saved overlays can be hidden or shown.
- The crossover table describes the selected result. Chart markers describe
  every visible SMA line; these scopes are intentionally different.
- Touch or click and hold inside the plot to select an x-range. The earlier
  boundary is always green, the later boundary red, and the selected area shaded.
  Crossing the original touch position changes the moving boundary's color.
- Release zooms to the chosen range and scales y to the visible prices and SMA
  values. Nested zoom is supported. Zoom out appears beside the title only
  while zoomed and restores the full history.
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

## Current app behavior and remaining work

The optimizer now searches under the agreed automatic cap, requires actual
usable coverage, and ranks candidates by warm-up-adjusted annual-frequency
error. The cards, explanation, chart, and table use this active result. Historical
saved lines remain viewable; those outside today's cap are labelled, not deleted
or treated as newly optimized results.

The app uses Python and Kivy's native canvas, with SQLite local persistence.
It is portrait-first with vertical scrolling; panning, pinch zoom, calendar
dates, exchange calendars, corporate-action adjustments, and return/backtest
analysis are not implemented. Kivy is the only direct third-party dependency.

The supplied LinkedIn article returned HTTP 403 and could not be read; the
implementation follows the written requirements and the recorded decisions.
Long genuine histories will need performance profiling and schema planning.

A longer default mock history, genuine market data,
background scheduling, and Android packaging are separate future changes.
These remain outside the current implementation.
