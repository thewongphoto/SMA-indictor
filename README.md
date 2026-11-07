# SMA Stock Analyzer

**Android 0.10.3:** a continuous GPU-rotated loading indicator, 12 saved-SMA colour
choices, VOO startup/guide data, the DBS company logo and offline logos for 30
major ETF providers. Read the
[Android testing/request-log guide](docs/YAHOO_ANDROID_TESTING.md) and
[release notes](docs/RELEASE_0_10_3.md). See the
[new screenshots](docs/design/ui-0.10.3/README.md),
[app flow](docs/design/ui-0.10/README.md) and
[Android notification test guide](docs/ANDROID_DAILY_NOTIFICATIONS.md).

Included from 0.10.2: animated pages/drawers/accordions, `SMA (X days)` labels,
matching custom inputs, Back-cancelable optimization and notification banners.

Included from 0.10.1: new saved SMA phone alerts and both signal types default
to On, preserving stored Off choices. The request log identifies each SMA,
signal, closing date and trigger/delivery outcome.

Included from 0.10.0: security selection and preferences share one animated screen;
saved SMAs can be named; enabled alerts have daily Singapore-time checks.
Charts/signals/comparisons continue using dividend/split-adjusted closes.

See [motion and alert behavior](docs/UI_MOTION_AND_ALERTS.md) for animation,
cancellation and banner-channel details.

The current **Kivy desktop preview** is available from this repository’s main branch. Follow [the Mac guide](START_HERE_MAC.md) or run `bash run-desktop.command`. See [Yahoo desktop testing](docs/YAHOO_DESKTOP_TESTING.md) for its data and calculation rules.

**The current desktop main branch adds private Yahoo EOD retrieval** with
persistent caches and full-history MAX. Follow the
[Yahoo desktop testing guide](docs/YAHOO_DESKTOP_TESTING.md). This update
keeps desktop fetching interactive. Android 0.10.3 is
requested separately through its APK build tag.

**Previous Android version 0.7.0** released the approved library-first UI, three-year guided
example and company logo/name chart heading. See the [release notes](docs/RELEASE_0_7_0.md).

**New to Python and using a Mac? Start with [the step-by-step Mac guide](START_HERE_MAC.md).**

A personal Python/Kivy app for finding a simple moving average whose
upward-crossing frequency is closest to a chosen target. The desktop Yahoo
preview downloads US/SG stock and ETF daily history for private use; analysis
stays local. The guided example and `DEMO-SGX`/`DEMO-US` remain fictional.
Android uses a portable HTTPS adapter for the same Yahoo search/chart subset;
the APK does not include the desktop yfinance native dependency stack.
iOS packaging and native background adapters remain separate work.
No Yahoo account/API key is normally required.

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
Desktop requirements install Kivy and the Yahoo dependencies; charts use
Kivy's native canvas. Base/mobile requirements remain separate. Android adds
Pyjnius and a Google Identity Gradle dependency.
SQLite and the test runner are part of Python's standard library.

From this repository directory on Linux/macOS:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-desktop.txt
python main.py
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-desktop.txt
python main.py
```

If PowerShell activation is restricted, run `.\.venv\Scripts\python.exe` in place
of `python`. Installation downloads dependencies; the desktop app retrieves
Yahoo prices when needed and retains them locally.
Desktop analysis needs no Android SDK. Live data requests require network access;
previously downloaded data remains available offline. For the current phone test APK, use the
[beginner Android APK guide](docs/ANDROID_APK_GUIDE.md).

## Security search

Type part of a ticker or company name, then press **Enter** or **Submit**. Search
results show packaged logos/initials, tickers, company names and exchanges. Only
selecting a result loads its history; keystrokes make no requests. This release
uses **Yahoo search for US/SG stocks and ETFs** on desktop, with persistent
submitted-query results and daily history. No Twelve Data calls are made.
The earlier [security search guide](docs/SECURITY_SEARCH.md) records the original
12-security simulation mode.

The original design for the private-use Yahoo feed is documented in the
[Yahoo Finance integration plan](docs/YAHOO_FINANCE_INTEGRATION_PLAN.md),
including endpoint/request budgets, persistent caching, full-history MAX and
owner preparation. See also [private iPhone installation](docs/PRIVATE_IPHONE_INSTALLATION.md).
The [desktop implementation/test guide](docs/YAHOO_DESKTOP_TESTING.md) records
what is implemented, live-connectivity limits and the deferred mobile work.

Version **0.6.0** uses a company logo and name in **Selected security**. Both saved
SMA menus show logo, company name and ticker; names shorten at whole-word
boundaries with an ellipsis while the ticker stays visible. Each expanded
security and its SMAs share a subtle rounded teal enclosure. Recently unsaved
lines show a smaller logo and company name. Packaged logos use an initials
fallback when no brand image is available. See [security identity UI](docs/SECURITY_IDENTITY_UI.md).

The approved [library-first full-app review](docs/design/library-first-review/README.md)
includes GitHub-previewable navigation maps and captures of every screen. The
[earlier alternatives](docs/design/README.md) remain available as design history.

## Screen navigation

The app opens on **My SMA library**. Yahoo mode shows saved real-company SMAs
and puts **New analysis** first when none exist. It starts with no selected
company or prices; old synthetic saves remain separate. The offline demo's
first card introduces moving averages and upward crossing buy signals.
**See the guided example** opens a three-year
simulation with frequency choices and investment comparisons. The guide explains
possible recovery signals, SMA lag, false crossings and the risk of subsequent falls.

**New analysis → Search → Parameters → Optimize SMA → Results** is the main
analysis path. Parameters has a collapsible **Custom** section. Results keeps
the heart, Hide/Show and **Change parameters**, which retains the selected
settings. Saved-line **View** opens exact saved parameters directly from Library.

**Section 03: Backtesting** places the period dropdown beside **If you invested
$100 for the past:**. It shows a: N upward crossings, b: N equal-period DCA buys,
and c: the most common of 500 random N-buy scenarios. All invest $100 per buy,
hold fractional units to the final close and show ending values only, with b/c
percentage differences relative to a. DCA starts at each equal interval's first
EOD close, including when N=1. Random sample arithmetic mean prices are rounded
to whole dollars; the most frequent dollar group supplies a representative
actual sample. Circled i buttons explain both comparisons.

The footer reports the percentage of the 500 random scenarios with an arithmetic
mean purchase price higher than a's mean crossing price. See the desktop guide
for exact mode/tie and percentile rules. This price rank is not necessarily an
ending-value rank. **View all upward crossings** retains the full event list.
Prices/dates are synthetic; crossing fills use interpolated daily-line
intersections, not observed intraday trades.

**Screen 2b** is a partial saved-lines bottom sheet. Saving a new configuration
opens it automatically; the fixed top Saved SMAs menu also opens/closes it. Swipe
the top handle downward or tap the dimmed area to dismiss it. Its list scrolls
independently, and the top toolbar stays reachable. Both saved libraries
group saved lines by security. Click the down arrow beside a security to expand
its SMA rows, and the up arrow to collapse them. Each row has View, Hide/Show,
heart and notification controls. Both menus share expansion state during the
session. Only matching counter/scenario lines are overlaid on a chart.

The **gear** on Library or the top Results toolbar opens **Settings**. Back
returns to the prior screen. Back dismisses overlays and the keyboard before
traversing pages; only Library exits. There is no Home/Saved/Learn bottom bar.

[View screenshots of every screen](docs/UI_PREVIEW.md).

## Try the offline demo

The details below describe the retained simulation mode. For the Yahoo desktop
flow use [the Mac walkthrough](START_HERE_MAC.md). To open the old offline demo
on macOS/Linux with separate folder-local saves:

```sh
bash run-desktop.command --demo
```

1. Choose New analysis, search a partial ticker/company name,
   press Enter/Submit, and select a match. Expand **Custom** on Parameters to
   choose **Trending**, **Oscillating**, or **Sideways**. All combinations use reproducible simulated closes, including
   the company examples; no live-data API is connected.
2. Choose **12**, **6**, or **1** upward crossings per trading year. Choose
   **Custom** to type another positive integer, then press **Optimize SMA**.
3. The teal price line is overlaid with the gold optimal SMA. Black-outlined plus signs mark
   upward crossings. The full-width Optimal SMA card and its save/hide actions
   sit above the chart. Target Crossing Frequency and Actual Crossing Frequency
   sit side by side below it. The raw crossing count appears in section 03.
4. Tap the **outline heart** in Optimal SMA to save a line locally (it turns red). Optimize another target to
   compare multiple overlays. Saved lines belong to their counter, scenario,
   and mock-data version; they reappear when you return to that combination.
5. Use **Hide/Show** for saved lines and **Hide/Show SMA line** for the
   current result. If a saved line has the same period as the selected result,
   the selected visibility controls that period, and it is drawn only once.
   The selected toggle lasts for the current result; saved-row toggles persist.
   Tap a red heart to unsave a line; the current analysis remains until changed.
   Open Saved SMAs with the top menu. Its history icon restores the
   last 10 unsaved configurations.

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

### Inspect EOD prices and pinch to zoom

Drag one finger inside the plot to move a vertical cursor to the nearest EOD
point. Its tooltip shows the simulated date, close and selected SMA's value,
including when that SMA is hidden. Warm-up/gap values are labelled unavailable.
The cursor remains on release; this gesture never zooms.

Two fingers switch the chart into pinch mode: spread to zoom in, bring them
closer to zoom out, around their midpoint. Lifting one finger ends the pinch;
the remaining finger cannot accidentally change the range or start a cursor.
Use **Zoom out**, or reselect a timeline preset, to restore the preset's range.
1Y, 3Y, 5Y and Max quick views remain. Prices and SMA values still use the full
history; chart gestures do not change crossing statistics or the backtest period.
Page scrolling remains available outside the plot.

In this offline demo, dates are **synthetic weekday labels** starting on
2021-01-04. Yahoo results instead use actual dates, currency and full downloaded
history; no exchange-holiday calendar is inferred from missing observations.

The window starts at 440 × 920 and supports narrower portrait sizes down to
320 pixels wide. Content scrolls vertically. On wider desktops the portrait
column remains centered. Landscape layouts are not designed for this stage.

The [implemented interface screenshots](docs/UI_PREVIEW.md) show the layout
against the approved design reference. At widths of at least 760 dp, the counter,
scenario, target and Optimize SMA controls share one row; narrower phones use
a two-by-two grid. Selectors have rounded borders and visible dropdown arrows.
At 620 dp and above the Optimal SMA value sits beside its save/hide buttons;
on smaller screens the buttons sit below it. Header spacing, typography, chart
grid/axis labels and centered symbol legend follow the mockup. Completed
optimization hides the routine status paragraph, while loading and errors remain
visible. The Yahoo desktop dependencies are separate from these native chart widgets.

To configure the target choices, edit `sma_analyzer/settings.py`:

```python
TARGET_FREQUENCIES = (12, 6, 1)
ALLOW_CUSTOM_TARGET = True  # False hides manual entry
```

Custom targets must fit a positive SQLite signed 64-bit integer. A target can
be mathematically unreachable: the app still displays the closest candidate
and its actual count instead of claiming an exact match.

## Hearts, history and notification previews

The manual delivery descriptions here apply to the retained demo/Android
features. Yahoo desktop notification/background testing is deferred; its delivery
test buttons are disabled.

Saved rows now show chart-matched colour dashes, separate **Push notifications
On/Off** controls, View, compact Hide/Show and a red
heart at the far right. The outline/red heart in Optimal SMA also saves/unsaves.
The clock/history icon in section 02 restores the ten most recently unsaved
configurations across all scenarios/counters; older entries are discarded.

The Parameters landing page now lists **all** saved counters/scenarios below
the form, including hidden lines. Tap a row or **View** to open its exact saved
period and target on Results; this does not re-optimize it. Results keeps its
Hide/Show controls. Both the bottom menu icon and **Saved SMAs** text open the
partial saved-lines sheet.

On Android, Back first closes an editor/popup/sheet, then returns to the previous
page. It exits only from Parameters. Native system-bar/cutout/keyboard geometry
keeps the app inside its usable surface and scrolls focused fields into view.
Phone keyboard behavior still needs retesting on the updated APK.

**Screen 3 / Notification Settings**, opened with the bottom-right gear, contains
phone Buy/Monitor switches and the EOD test session field. Each saved line also
has a phone On/Off control. Both the per-line control and its type switch must
be On. There are no recipient, email, Connect Gmail, disconnect or email-test
controls. Legacy email preferences remain in SQLite for upgrade compatibility,
but this application ignores them for preview and delivery.

Press **Preview EOD alerts** for a simulated session to see phone text without
posting anything. **Send enabled alerts** requests Android notification permission
and posts the selected phone alerts. Successful events are deduplicated. The
generic **Test Android phone notification** remains repeatable. Denying permission
returns a helpful message and re-enables the controls.

Those older demo alerts had no remote push server, daily
scheduler or live EOD-price source. The APK guide's old Gmail sections are
historical and do not apply to version 0.4.0.

The existing [APK workflow](.github/workflows/android-debug.yml) supports manual
runs on main and intentional `apk-v*` release-tag pushes. It runs the unit/UI
checks before packaging and uploads `sma-android-test` with the APK and logs.
The original signing identity is retained so Android updates can keep local data.

Follow [signing preservation](docs/ANDROID_SIGNING.md) once to keep the original
SHA-1 in a durable Actions secret. The build now refuses to silently replace
a missing signing key. Use the [Android release checklist](docs/ANDROID_RELEASE_CHECKLIST.md)
for every future APK; automated unit/UI checks also run before packaging.

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
The history-length update preserves these parameters. The notification update
adds columns/tables automatically without changing existing periods or targets.

## Run automated checks

Engine, mock-data, presentation model, and SQLite tests need **no Kivy or GUI**:

```sh
python -m unittest discover -s tests -v
```

The real-widget smoke runner starts Kivy, dispatches button/selector events,
waits for asynchronous calculations, and checks the displayed cards, actual
chart arrays/markers, investment values/period controls, crossing details, saving, visibility, input errors, empty data,
and 320×640, 440×920, 560×1000, 760×1100 and 960×1440 portrait sizes. It also sends synthetic
touches through the real window/scroll-view pipeline to test snapped EOD inspection,
two-finger spread/contract, finger lift, outside-plot release, and the zoom-out button:

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
| Standard-library test suite | **100 passed** in the full suite; 0 failed, 0 skipped |
| Real Kivy UI smoke checks | **43 groups passed**, 0 failed; Android/library, preview and security-search regressions included |
| Portrait rendering | 320×640, 440×920, 560×1000, 760×1100, 960×1440 exercised |
| Screenshot exports | Parameters, results, full crossovers, saved sheet and settings generated and inspected |
| Dependency compatibility | `python -m pip check` passed |
| Gmail Java bridge compile | Old Google library reproduces the 3 errors; replacement 21.4.0 passes against real Android API 35/Google libraries |
| Android window/insets helper | Compiles against real Android API 35 |
| Signing identity | Real keytool secret-restore round trip preserves SHA-1; unavailable key fails closed |
| Android APK build | User installed the prior APK; 0.2.1 needs a fresh workflow run on main |
| Physical Android / Google consent / real sending | Generic phone notification passed per user report; 0.2.1 fixes and Gmail sending need device tests |

Tests include requested A–G, missing data, invalid inputs, a 3-year target,
all six counter/scenario combinations, SQLite reload and deduplication,
visibility, and empty history with saved lines. See `PROGRESS.md` for the handoff. The latest run also checked the five-year
default and seeded prefix, timeline availability, whole-button dropdown clicks,
selected-option shading, same-preset reset, outlined plus markers, revised
card hierarchy, and full-history result stability while changing views.
Gesture checks cover one-finger EOD inspection, continuous two-finger zoom in/out,
visible y-limits including SMA values, finger lift, release beyond the plot,
page scrolling, reset on new data, unchanged full-history calculations, and the
actual zoom-out control. See docs/ANDROID_TEST_STATUS.md for current limitations.

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
recomputed from the deterministic dataset. The recipient email/preferences are
stored locally; no financial credentials or Google refresh tokens are stored. Back up the database to preserve saved lines; deleting
it resets them. The current additive migration preserves existing lines while adding channel flags,
last-10 unsaved history, recipient/type preferences and successful-delivery keys.
No passwords or provider credentials are stored. Future genuine market data needs
its own schema and migrations.

```text
main.py                    # Launches the Kivy application
requirements.txt           # Base/mobile Kivy + certifi; unittest/SQLite are built in
requirements-desktop.txt   # Base plus desktop Yahoo dependencies
sma_analyzer/
  settings.py              # Frequency presets, mock choices, version
  engine.py                # SMA, events, capped annual-frequency optimizer
  policy.py                # Automatic cap, observable coverage, exact annual rates
  mock_data.py             # Seeded five-year (1,260-session) synthetic series
  storage.py               # SQLite lines, history, preferences, delivery dedup
  notifications.py         # EOD rules, Android notifications and channel dispatch
  gmail.py                 # Send-only Gmail MIME/HTTPS transport
  android_gmail.py         # Lazy native Google Identity authorization bridge
  model.py                 # Shared chart/card/table presentation state
  chart.py                 # Android-compatible Kivy canvas chart
  viewport.py              # Timeline presets, inclusive zoom ranges, y scaling
  navigation.py            # Animated saved-lines sheet and downward swipe handle
  widgets.py               # Shared rounded selectors and symbol legend
  app.py                   # Portrait UI and asynchronous button actions
android/                   # Google Identity Java bridge and notification icon
buildozer.spec             # Portrait ARM64 debug APK, permissions and dependencies
requirements-android.txt   # Build-tool environment; separate from desktop
.github/workflows/         # Manual test-APK build + fingerprint/artifact upload
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

Known limits: synthetic five-year datasets, synthetic dates with no exchange calendar,
no price adjustments, no return/backtest analysis, no separate pan gesture,
one calculation worker, and no Android device/keyboard/lifecycle validation.
An exhaustive search is suitable for this prototype but will need profiling for
long genuine histories. Saved-line visibility is persistent; the active analysis
and dropdown selections are session state.

After you approve the next stage: introduce an explicitly selected data source
with adjusted EOD closes, timestamps, corporate-action and missing-session
rules, a versioned local cache, and fixture-based integration tests. Revisit
warm-up exposure with you before changing the objective. Then validate native
Android touch, keyboard, safe areas, pause/resume and persistence using the
authorized debug-build guide. Buildozer configuration is now included; Google
account setup is described in that guide. Release-store packaging remains later work.
The desktop branch now integrates Yahoo EOD retrieval for private testing.
No background EOD scheduler or Play Store release is included.
Phone notifications and the debug-APK build configuration are implemented.
Version 0.4.0 removes email/Gmail functionality from the application UI and delivery flow;
new APK/device validation remains required.
