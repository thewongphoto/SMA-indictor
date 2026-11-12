# SMA Stock Analyzer

A private Python/Kivy app for US and Singapore stocks and ETFs. It finds the
SMA whose historical upward-crossing frequency is closest to a chosen target,
plots dividend/split-adjusted closes and compares three investment strategies.

| Platform | Current status |
| --- | --- |
| Android | Signed release APK distribution through GitHub Actions. Source version **0.13.7**. |
| Mac / desktop | Active Kivy app with real data and persistent local storage. |
| iPhone | Native releases paused. The Vercel/PWA guide is a plan; this repository does not yet contain the web frontend or a deployed website. |

A published tag requests a build; it does not establish that an APK is ready.
Check the [Android workflow](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml)
for a successful run and download its **sma-android-test** artifact.

## Start here

- [Install or update the Android APK](docs/ANDROID_APK_GUIDE.md).
- [APK signing, package security and Play Protect review](docs/ANDROID_PACKAGE_SECURITY.md).
- [Run on a Mac](START_HERE_MAC.md).
- [Deploy a future iPhone web app through Vercel](docs/PRIVATE_IPHONE_INSTALLATION.md).
- [All current guides](docs/1.Directory.md), [release history](docs/CHANGELOG.md),
  [validation status](docs/ANDROID_TEST_STATUS.md) and [cleanup record](docs/MAINTENANCE.md).

## Current features

- Partial ticker/company search runs only on Enter or Submit. Selecting a match
  downloads history; typing does not make requests. Supported US/SG stocks and
  ETFs have bundled company/issuer logos or an initials fallback.
- Full available history, persistent search/price caches, visible connection
  errors and a copyable request log. Reopening the app does not clear data.
- Library-first navigation with grouped saved SMAs, custom names, twelve
  persistent colours, Hide/Show, notification switches and a ten-entry archive.
- Live targets use **365 calendar days per year**, including weekends/holidays.
  This is the closest historical annualized average, not a guaranteed annual
  quota. SMA (X days) means X trading observations. Saved periods stay fixed.
- Charts offer 3M/6M/9M/1Y/3Y/5Y/Max, smooth two-finger pinch and one-finger EOD
  inspection. Visible endpoint changes show currency/% values and direction
  arrows; a pinched view shows actual endpoint dates.
- Backtesting compares crossing entries, equal-period DCA and the representative
  result of 500 random samples. It shows contributions, ending values and the
  requested comparisons. [Exact rules](APP_SUMMARY.md).
- The live guided example uses Vanguard S&P 500 ETF (VOO), initially 4/year and
  Max. The upward-crossing app logo draws continuously during optimization;
  Back/Escape cancels and cached targets open immediately.
- Android has three phone signal types, daily scheduled checks and background
  diagnostics. [Schedules and testing](docs/ANDROID_DAILY_NOTIFICATIONS.md).

Prices and calculations use adjusted daily closes. Crossing prices are
interpolated daily-line intersections, not observed intraday trades. Fees,
taxes and currency movements are excluded from return comparisons. Frequency
matching is not a claim of profitability. Yahoo data remains for private use.

## Development

Use Python 3.12 for desktop and the pinned Python 3.11 Linux toolchain for APK
validation. The Mac launcher installs the desktop dependencies:

```sh
bash run-desktop.command
```

For another desktop, create a virtual environment, install
`requirements-desktop.txt`, then run `python main.py`. Explicit offline fixtures
remain available through `bash run-desktop.command --demo`; they are separate
from real histories and saved parameters.

The [developer release checklist](docs/ANDROID_RELEASE_CHECKLIST.md) lists the
unit and all eight UI gates. Keep signing keys, caches and local databases out
of Git. Install APK updates over the existing app; preserve its signing key and
package ID. [Signing guide](docs/ANDROID_SIGNING.md).

[Current screenshots and animation](docs/design/README.md) use controlled test
data. Retired mockups and older documents remain accessible in Git history.
