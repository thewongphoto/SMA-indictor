# Review the Kivy desktop preview

The desktop preview and Mac launcher are available on GitHub's **main** branch.
Version 0.4.0 also prepares these changes for an APK release and removes email
notification/Gmail controls and sending from the application. Phone notifications
and existing saved data are retained.

## Run on your Mac

1. Open [the repository](https://github.com/thewongphoto/SMA-indictor), select
   **main**, then click **Code → Download ZIP**.
2. Extract the ZIP. Open Terminal, type `cd `, drag the newly extracted
   **SMA-indictor-main** folder into Terminal, and press Return.
3. With Python 3.12 installed, run:

   ```sh
   bash run-desktop.command
   ```

The beginner walkthrough is [START_HERE_MAC.md](../START_HERE_MAC.md).

The launcher prepares `.venv`, installs the desktop requirements, and opens the
native Kivy window. Internet access is needed for the first dependency install.
It uses `.local/preview-data` for an isolated preview SQLite database. Your
phone and other desktop app data are unaffected. Later launches use the same
command and preserve this preview's saved SMAs.

For Windows, use Python 3.12 to create a virtual environment and run `main.py`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SMA_ANALYZER_DATA_DIR = "$PWD\.local\preview-data"
.\.venv\Scripts\python.exe main.py
```

## What to check

- Search a partial ticker/company name, then press Enter or Submit. Confirm
  typing alone does nothing, matches display logo/ticker/name, and selecting one
  loads simulated history. The default fictional selection remains usable.
  See [Security search](SECURITY_SEARCH.md) for the 12-security preview catalogue.

- Optimize a counter/scenario. Plus markers sit on the intersection of the
  price/SMA line segments; the event table shows crossing prices. A one-finger
  drag still inspects EOD points; two-finger gestures still control zoom.
- Section 03 has its period dropdown beside **If you invested $100 for the past:**.
  Scenario a shows N crossings, b shows N equal periods, and c shows N random
  points (most common scenario). Only ending dollar values are shown, with b/c
  percentage differences relative to a.
- The circled i buttons open help for DCA and the random comparison.
- Save multiple SMAs across both securities. On Parameters and in the Results
  saved sheet, each security starts collapsed. Its arrow expands/collapses its
  SMA list. Expanded state is shared between those menus during the session.
  Each row has View, Hide/Show, heart and notification controls.

## Calculation rules

Each scenario invests **$100 per purchase**, holds fractional units to the final
EOD close, and uses the same number N of purchases. Costs/dividends are omitted.

**a: Crossing purchases.** Crossings still use the existing below-to-above rule,
including equality/gap handling. The two daily price/SMA segments are interpolated
to locate their intersection. Both the marker and purchase price use that point.
The confirming daily session still determines inclusion in the selected period.
This is a geometric simulation from daily data, not an observed intraday fill;
its interpolation uses the next daily endpoint. It cannot establish achievable
live-trading returns. Crossing counts and frequency-based SMA selection are
unchanged. Dates and prices remain simulated.

**b: Equal periods (DCA).** Divide the chosen window's trading sessions into N
intervals and buy at each interval's first EOD close, including the first close
of the window when N=1. N=2 buys at the start and halfway through. Scheduled
session indices round down. Missing closes move to the next valid date, subject
to preserving distinct dates and enough remaining dates for the remaining buys.
DCA and random dates span the full chosen window, including SMA warm-up dates.

**c: Most common random scenario.** Generate 500 samples using seeds 0–499; each
sample chooses N distinct valid EOD dates. Compute its arithmetic mean purchase
price and round it to the nearest whole dollar (half dollars round up). Select
the most frequent dollar value. If modes tie, choose the one closest to the
median of all sample means, then the lower dollar. Within that group, use the
sample whose mean is closest to that modal dollar; lowest seed breaks ties.
Its actual individual buys determine the displayed ending value. We do not
convert the entire budget at the arithmetic mean price, which would misstate
units bought by equal-dollar purchases.

**Outperformance Y%.** Count all random samples whose unrounded arithmetic mean
purchase price is strictly greater than a's mean crossing price, divide by 500,
and multiply by 100. Ties do not count. This is the requested average-price rank;
it is not necessarily a rank of ending portfolio values. With N=0 all values
are zero and percentages are N/A.

## Cloud validation

- 93 standard-library tests passed, including interpolation, DCA scheduling,
  500-seed mode selection, rounding/ties, and the requested price-rank statistic.
- 33 full real-widget UI groups passed, followed by five focused preview groups
  exercising the new captions, popups, zero crossings, exact marker coordinates,
  security accordions, and independent cross-security row controls.
- No actual laptop execution or Android APK build is claimed by these cloud checks.

For a local smoke test with a working display, run:

```sh
bash run-desktop.command --smoke-test --preview-rules-only
```
