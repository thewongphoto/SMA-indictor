# SMA Stock Analyzer

**New to Python and using a Mac? Start with [the step-by-step Mac guide](START_HERE_MAC.md).**

A personal, **offline Python/Kivy prototype** for finding a simple moving average
whose upward-crossing frequency is closest to a chosen target. Every price is
synthetic. `DEMO-SGX` and `DEMO-US` are **fictional counters**, not exchange feeds.
The app makes no network requests and needs no account, credentials, or backend.

This is frequency matching, **not evidence of a profitable trading strategy**.

Read [the app summary and calculation conditions](APP_SUMMARY.md) for the recorded
rules, limitations, implementation status, and material for a future printed
summary.

The app now uses the agreed **warm-up-adjusted annual frequency**, automatic
history-dependent SMA cap, and minimum observable-history requirement. It shows
one actual annual frequency. The mock datasets now contain five years (1,260 sessions). The
[pre-integration evaluation](docs/observable-frequency-evaluation.md) records why
these rules were chosen; the production code is in `engine.py` and `policy.py`.

## Install and launch

Use Python **3.12** (tested with 3.12.14) and a desktop with graphics support.
Kivy is the only direct third-party dependency; charts use its native canvas.
SQLite and the test runner are part of Python's standard library.

From this repository directory on Linux/macOS:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

If PowerShell activation is restricted, run `.\.venv\Scripts\python.exe` in place
of `python`. Installation downloads dependencies; the running app uses mock data
only. No Android SDK, Java, Buildozer, or emulator is required for this stage.

## Try the prototype

1. Choose a fictional counter and **Trending**, **Oscillating**, or **Sideways**.
   Each combination has 1,260 reproducible synthetic closes and a fixed seed.
2. Choose **12**, **6**, or **1** upward crossings per trading year. Choose
   **Custom** to type another positive integer, then press **Optimize SMA**.
3. The teal price line is overlaid with the gold optimal SMA. Black-outlined plus signs mark
   upward crossings. The full-width Optimal SMA card and its save/hide actions
   sit above the chart. Target Crossing Frequency and Actual Crossing Frequency
   sit side by side below it. The raw crossing count appears in section 03.
4. Press **Save SMA line** to retain a line locally. Optimize another target to
   compare multiple overlays. Saved lines belong to their counter, scenario,
   and mock-data version; they reappear when you return to that combination.
5. Use **Hide/Show** for saved lines and **Hide/Show SMA line** for the
   current result. If a saved line has the same period as the selected result,
   the selected visibility controls that period, and it is drawn only once.
   The selected toggle lasts for the current result; saved-row toggles persist.
   Removing a saved line leaves the current analysis available until changed.

Changing a scenario, counter, or target clears the selected statistics. Press
Optimize again to compute the new result; saved overlays remain available.
The event table always describes the **selected result**, even when its line
is hidden. The chart's plus markers describe **all currently visible SMA lines**.

### Default timeline view

The rounded dropdown below the counter/scenario title starts at **1Y** whenever
an app session or a new counter/scenario starts. Its label and downward arrow
share one clickable area. Choose **1Y**, **3Y**, **5Y**, or **Max**; 3Y is omitted
below 756 sessions and 5Y below 1,260. 1Y clamps to all data if less than a year
is available, and Max shows everything. The latest sessions are always used.

Timeline changes do not alter the optimizer's input or crossing statistics.
Re-selecting a preset resets any custom drag zoom within that preset. Gold/teal
dash symbols identify SMA/close lines in the legend, and the outlined plus
symbol identifies upward crossings, without color-name prefixes or colons.

### Zoom into a chart range

Press and hold inside the plot, then drag left or right (on a Mac, click and
hold with the mouse or trackpad). A vertical line appears immediately. While
dragging, the **left/start boundary is green**, the **right/end boundary is red**,
and the selected area is shaded. If you cross your original touch point, the
moving boundary changes color to keep that ordering.

Release to zoom to the selected sessions. The y-axis automatically scales to
the visible prices and displayed SMA lines, with a little padding. The small
**Zoom out** button appears at the top right beside the counter/scenario title;
click it to restore the selected timeline preset. It disappears when no custom
selection zoom is active; choose Max to display all available sessions.

You can drag again for a closer zoom. Selections round outward to include both
bordering sessions; taps or horizontal movements under 6 display-independent
pixels do not zoom. A drag that leaves the plot is clamped to the plot's x-range.
Scroll the page by starting a swipe outside the plot, or use the mouse wheel.
Changing the counter or scenario resets zoom. Optimizing a new target or
hiding/showing a line keeps the current range and updates the y-axis.

Zoom changes only the view: SMAs are still calculated from the full history,
including prices before the visible range. Crossing statistics and the table
still describe the full-history analysis; only visible crossover markers are
drawn on the chart. There is no panning or pinch zoom in this stage.

The window starts at 440 × 920 and supports narrower portrait sizes down to
320 pixels wide. Content scrolls vertically. On wider desktops the portrait
column remains centered. Landscape layouts are not designed for this stage.

To configure the target choices, edit `sma_analyzer/settings.py`:

```python
TARGET_FREQUENCIES = (12, 6, 1)
ALLOW_CUSTOM_TARGET = True  # False hides manual entry
```

Custom targets must fit a positive SQLite signed 64-bit integer. A target can
be mathematically unreachable: the app still displays the closest candidate
and its actual count instead of claiming an exact match.

## Mathematical rules

For period `N`, `SMA[t] = sum(P[t-N+1:t+1]) / N`.

* `simple_moving_average(prices, N)` returns one value per input session.
  The first `N-1` values are `None`. A period longer than the available history
  raises a helpful `ValueError`. Period 1 is supported by this function.
* Each SMA needs `N` consecutive finite observations. `None`, NaN, and infinity
  are treated as missing; they restart the SMA warm-up. Other nonnumeric input
  is rejected. Calculations use full precision; only display values are rounded.
* A crossover is a transition from **strictly below** to **strictly above** the
  SMA. The first valid side establishes a baseline and never counts as an event.
* Exact equality keeps the last strict side. Thus `below → equal → above`
  counts once, while `above → equal → above` does not. An initial equality
  supplies no baseline. Missing price/SMA values reset the baseline, preventing
  crossings across gaps. Floating-point comparisons use strict numeric equality,
  with no hidden epsilon. The event is recorded at the first strictly above session.
* `crossover_events(prices, sma)` returns zero-based indices and exact price/SMA
  values; `count_crossings(prices, sma)` returns the count. UI session numbers
  are one-based, **not calendar dates**.

The optimizer searches every integer period from 2 through an automatic cap.
For input length H, the cap is `min(floor(H/2),252)` through 756 sessions and
`H-504` above 756 sessions. It is not user-configurable. Each candidate must have
at least `H-cap` actual observable comparisons. Histories over three years
therefore retain at least two usable trading years; shorter histories can have
less. At least four input sessions are needed to admit SMA 2.

A usable comparison requires finite prices and SMA values on two consecutive
observations. Warm-up, gaps, and re-warm-up are excluded. With complete history
and period N there are **H-N comparisons**: the first SMA supplies a baseline.

```text
usable years = observable comparisons / 252
actual crossings/year = crossing count / usable years
error = abs(actual crossings/year - selected target/year)
```

All observable history contributes, not just the last year or the zoomed region.
Smallest annual-frequency error wins; exact rational ties choose the shorter
SMA. Explicit candidate lists used in tests obey the same cap and coverage rules.
If no candidate has enough valid coverage, optimization gives a helpful error.

The interface shows only the adjusted annual frequency, with crossing count,
usable comparisons/years, candidate cap, and annual target difference for context.
A target may be unattainable. With the current five-year DEMO-SGX Sideways data and target
12, the closest eligible result is **SMA 254: 125 crossings over 1,006 comparisons,
31.31/year**. Oscillating selects SMA 721: 26 crossings over 539 comparisons,
12.16/year. Annualization does not guarantee future frequency or profits.

Saved lines from earlier versions remain available and retain their original
period and target. Lines above the current cap are labelled as previously saved
and outside the current search limit; they are not silently retuned or deleted.
The database needs no migration because it stores parameters, not derived rates.

## Run automated checks

Engine, mock-data, presentation model, and SQLite tests need **no Kivy or GUI**:

```sh
python -m unittest discover -s tests -v
```

The real-widget smoke runner starts Kivy, dispatches button/selector events,
waits for asynchronous calculations, and checks the displayed cards, actual
chart arrays/markers, table cells, saving, visibility, input errors, empty data,
and 320×640, 440×920, and 560×1000 portrait sizes. It also sends synthetic
touches through the real window/scroll-view pipeline to test range selection,
boundary colors/shading, nested zoom, outside-plot release, and the zoom-out button:

```sh
python -m scripts.smoke_ui
```

It uses an isolated temporary database and exits on completion. It writes
`artifacts/ui-smoke.json`, `artifacts/prototype-phone.png`, and
`artifacts/prototype-full.png`, plus `artifacts/zoom-*.png` for selection and
zoomed views. Reports and screenshots are generated outputs,
ignored by Git. This is a running-widget integration check; it does not replace
manual touchscreen testing on Android.

### Headless cloud environment

This instance successfully ran Kivy using SDL's offscreen driver and Mesa
software OpenGL. From `/workspace/SMA-indictor`:

```sh
mkdir -p .local/kivy .local/cache artifacts
KIVY_HOME="$PWD/.local/kivy" \
XDG_CACHE_HOME="$PWD/.local/cache" \
KIVY_NO_ARGS=1 SDL_VIDEODRIVER=offscreen LIBGL_ALWAYS_SOFTWARE=1 \
KIVY_CLIPBOARD=dummy .venv/bin/python -m scripts.smoke_ui
```

Open the exported PNG files to inspect the UI when a desktop display is
unavailable. For an interactive window, use `python main.py` on your computer
without `SDL_VIDEODRIVER=offscreen`. No web server or browser preview is needed.
Offscreen support depends on the host's SDL/OpenGL drivers; the standard-library
test suite remains usable without them. Kivy can emit a cutbuffer warning about
missing `xclip`/`xsel` on headless Linux; the tested controls still work, while
system clipboard integration is unavailable there.

### Validation in this environment

The completed prototype was validated with Python 3.12.14, Kivy 2.3.1,
SDL2, and Mesa llvmpipe software OpenGL:

| Check | Actual result |
| --- | --- |
| Standard-library test suite | **44 passed**, including production/reference integration checks, 0 failed, 0 skipped |
| Real Kivy UI smoke checks | **17 groups passed**, 0 failed |
| Portrait rendering | 320×640, 440×920, 560×1000 exercised |
| Screenshot exports | Phone viewport and full scrollable page generated and inspected |
| Dependency compatibility | `python -m pip check` passed |
| Android device / APK build | Not run; deferred to the next approved stage |

Tests include requested A–G, missing data, invalid inputs, a 3-year target,
all six counter/scenario combinations, SQLite reload and deduplication,
visibility, and empty history with saved lines. See `PROGRESS.md` for the handoff. The latest run also checked the five-year
default and seeded prefix, timeline availability, whole-button dropdown clicks,
selected-option shading, same-preset reset, outlined plus markers, revised
card hierarchy, and full-history result stability while changing views.
Zoom checks cover both drag directions, crossing the anchor, immediate visual
feedback, nested ranges, visible y-limits including SMA values, tap/jitter
rejection, release beyond the plot, a second finger, page scrolling, reset on
new data, unchanged full-history calculations, and the actual zoom-out control.

## Local data and project layout

By default `saved_lines.sqlite3` lives in Kivy's per-user application data
directory. Override it with `SMA_ANALYZER_DATA_DIR` (a directory path) for local
development or testing; it is not a credential. For a locked-down cloud launch:

```sh
KIVY_HOME="$PWD/.local/kivy" SMA_ANALYZER_DATA_DIR="$PWD/.local/data" python main.py
```

The SQLite table stores integer IDs, counter/scenario strings, SMA period,
target frequency, visibility (0/1), and a mock-data version. A uniqueness
constraint prevents duplicate saves. Derived series and event counts are
recomputed from the deterministic dataset. No user identity or financial
account data is stored. Back up the database to preserve saved lines; deleting
it resets them. Future genuine market data needs its own schema and migrations.

```text
main.py                    # Launches the Kivy application
requirements.txt           # Kivy only; unittest/SQLite need no package
sma_analyzer/
  settings.py              # Frequency presets, mock choices, version
  engine.py                # SMA, events, capped annual-frequency optimizer
  policy.py                # Automatic cap, observable coverage, exact annual rates
  mock_data.py             # Seeded five-year (1,260-session) synthetic series
  storage.py               # Local SQLite saved-line repository
  model.py                 # Shared chart/card/table presentation state
  chart.py                 # Android-compatible Kivy canvas chart
  viewport.py              # Timeline presets, inclusive zoom ranges, y scaling
  widgets.py               # Rounded timeline dropdown and symbol legend
  app.py                   # Portrait UI and asynchronous button actions
tests/
  test_engine.py           # Arithmetic and algorithm rules
  test_model.py            # Mock data, controls, chart/table data, SQLite
  test_viewport.py         # Drag direction, nested ranges, reset, y-limits
scripts/
  smoke_ui.py              # Running-widget integration checks and PNGs
PROGRESS.md                # Completed work, known issues, next stage
```

## Source context and next stage

The supplied [LinkedIn write-up](https://www.linkedin.com/pulse/finding-optimal-ma-enter-any-stock-your-desired-frequency-kelly-wong/)
returned **HTTP 403** during implementation, so its contents could not be read.
The prototype implements the detailed rules in your request; it does not claim
to reproduce unverified details from that article. Pasted article text can be
compared with these rules in a later session.

Known limits: synthetic five-year datasets, no date axis or exchange calendar,
no price adjustments, no return/backtest analysis, no panning or pinch zoom,
one calculation worker, and no Android device/keyboard/lifecycle validation.
An exhaustive search is suitable for this prototype but will need profiling for
long genuine histories. Saved-line visibility is persistent; the active analysis
and dropdown selections are session state.

After you approve the next stage: introduce an explicitly selected data source
with adjusted EOD closes, timestamps, corporate-action and missing-session
rules, a versioned local cache, and fixture-based integration tests. Revisit
warm-up exposure with you before changing the objective. Then validate native
Android touch, keyboard, safe areas, pause/resume, and persistence, and prepare
Buildozer/python-for-android configuration with portrait orientation. Any
provider credentials should be configured securely only at that later stage.
No live API, scheduling, messaging, APK, or release build is included now.
