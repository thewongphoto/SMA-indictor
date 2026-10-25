# SMA Stock Analyzer

**New to Python and using a Mac? Start with [the step-by-step Mac guide](START_HERE_MAC.md).**

A personal, **offline Python/Kivy prototype** for finding a simple moving average
whose upward-crossing frequency is closest to a chosen target. Every price is
synthetic. `DEMO-SGX` and `DEMO-US` are **fictional counters**, not exchange feeds.
The app makes no network requests and needs no account, credentials, or backend.

This is frequency matching, **not evidence of a profitable trading strategy**.

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
   Each combination has 252 reproducible synthetic closes and a fixed seed.
2. Choose **12**, **6**, or **1** upward crossings per trading year. Choose
   **Custom** to type another positive integer, then press **Optimize SMA**.
3. The teal price line is overlaid with the gold selected SMA. Triangles mark
   upward crossings. Scroll below the chart for the selected period, target,
   actual annual rate, raw crossing count, and crossover table.
4. Press **Save SMA line** to retain a line locally. Optimize another target to
   compare multiple overlays. Saved lines belong to their counter, scenario,
   and mock-data version; they reappear when you return to that combination.
5. Use **Hide/Show** for saved lines and **Hide/Show selected SMA** for the
   current result. If a saved line has the same period as the selected result,
   the selected visibility controls that period, and it is drawn only once.
   The selected toggle lasts for the current result; saved-row toggles persist.
   Removing a saved line leaves the current analysis available until changed.

Changing a scenario, counter, or target clears the selected statistics. Press
Optimize again to compute the new result; saved overlays remain available.
The event table always describes the **selected result**, even when its line
is hidden. The chart's triangles describe **all currently visible SMA lines**.
There is no pan/zoom in this first prototype.

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

The default optimizer searches **every period from 2 to `history length - 1`**,
inclusive. N=1 is excluded because it always equals the price. Each candidate
requires at least two adjacent valid SMA observations. Every candidate uses its
own valid observations across the **entire history**, after its warm-up.

```text
years = number of input trading sessions / 252
target count = selected crossings/year × years
error = abs(actual crossing count - target count)
actual crossings/year = actual crossing count / years
```

For 756 sessions and a target of 12/year, the target count is 36. Fractional
targets for partial years are compared directly without rounding. The smallest
error wins; ties always choose the **shorter SMA**, independent of candidate
order. For Test B's `[10, 12, 10, 12, 10, 12]`, period **2** gives events at
zero-based indices **3 and 5** (displayed sessions 4 and 6).

The full history, including warm-up and missing sessions, supplies the year
denominator. **This deliberately follows the requested whole-history method**.
Long SMAs have fewer eligible observations and may be favored when targeting
rare crossings. No warm-up extrapolation or trading-session calendar inference
is performed. A future common-window or valid-exposure method would be a
different optimization objective and should be added as an explicit option.

## Run automated checks

Engine, mock-data, presentation model, and SQLite tests need **no Kivy or GUI**:

```sh
python -m unittest discover -s tests -v
```

The real-widget smoke runner starts Kivy, dispatches button/selector events,
waits for asynchronous calculations, and checks the displayed cards, actual
chart arrays/markers, table cells, saving, visibility, input errors, empty data,
and 320×640, 440×920, and 560×1000 portrait sizes:

```sh
python -m scripts.smoke_ui
```

It uses an isolated temporary database and exits on completion. It writes
`artifacts/ui-smoke.json`, `artifacts/prototype-phone.png`, and
`artifacts/prototype-full.png`. Reports and screenshots are generated outputs,
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
| Standard-library test suite | **16 passed**, 0 failed, 0 skipped |
| Real Kivy UI smoke checks | **9 groups passed**, 0 failed |
| Portrait rendering | 320×640, 440×920, 560×1000 exercised |
| Screenshot exports | Phone viewport and full scrollable page generated and inspected |
| Dependency compatibility | `python -m pip check` passed |
| Android device / APK build | Not run; deferred to the next approved stage |

Tests include requested A–G, missing data, invalid inputs, a 3-year target,
all six counter/scenario combinations, SQLite reload and deduplication,
visibility, and empty history with saved lines. See `PROGRESS.md` for the handoff.

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
  engine.py                # Pure SMA, events, and exhaustive optimizer
  mock_data.py             # Seeded 252-session synthetic series
  storage.py               # Local SQLite saved-line repository
  model.py                 # Shared chart/card/table presentation state
  chart.py                 # Android-compatible Kivy canvas chart
  app.py                   # Portrait UI and asynchronous button actions
tests/
  test_engine.py           # Arithmetic and algorithm rules
  test_model.py            # Mock data, controls, chart/table data, SQLite
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

Known limits: synthetic 252-session datasets, no date axis or exchange calendar,
no price adjustments, no return/backtest analysis, basic unzoomed canvas chart,
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
