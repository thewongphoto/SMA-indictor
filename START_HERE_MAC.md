# Start here on a Mac

This runs the current **0.14.2 Kivy desktop app** with real Yahoo daily data.
It is a desktop app, not the future iPhone website. For iPhone, read the
[Vercel/PWA guide](docs/PRIVATE_IPHONE_INSTALLATION.md).

## 1. Install Python

Install Python **3.12** for macOS from python.org. Open Terminal and check:

```sh
python3.12 --version
```

A graphical macOS desktop is required to show Kivy. No Android SDK, Xcode,
Apple signing or Yahoo API key is normally needed for this desktop route.

## 2. Download the current source

Open [SMA-indictor on GitHub](https://github.com/thewongphoto/SMA-indictor), select
**main → Code → Download ZIP**, then unzip it. Keep older folders until the
updated app works. Source ZIPs and prebuilt Android APKs are different downloads.

## 3. Open the project in Terminal

Type `cd ` (including its trailing space), drag the unzipped folder into
Terminal, then press Enter. The folder should contain run-desktop.command,
main.py and requirements-desktop.txt.

```sh
bash run-desktop.command
```

The launcher creates its virtual environment, installs desktop dependencies
and opens a portrait Kivy window. Keep Terminal open while using it. On later
visits, run the same command from the project folder.

## 4. Try the app

1. My SMA library is the landing page. Select New analysis, type Apple/VOO/DBS,
   press Enter or Submit, then choose a match. Typing alone makes no requests.
2. The same page reveals preferences. Choose a target and Optimize SMA.
   The animated logo repeats during uncached calculations; Escape cancels.
3. Inspect an EOD point with the mouse. Use 3M/6M/9M/1Y/3Y/5Y/Max quick views;
   actual pinch needs a device/input provider that supplies two touches.
   The chart compares the first/last visible adjusted closes beneath its title.
4. Save with the heart. A saved line has a palette and rename pencil; names,
   twelve colour choices and preferences survive a restart. Groups start closed.
5. Use the independent backtest horizon, including Custom years. The guided
   example uses Vanguard S&P 500 ETF (VOO), initially 4/year and Max.
6. Settings contains connection checks, price refreshes and the copyable request
   log. [Current rules and navigation](APP_SUMMARY.md).

Live history/returns use dividend-and-split-adjusted prices. Crossing fills are
interpolated daily-line intersections, not observed intraday trades. Frequency
is the closest historical average per **365 calendar days**, not an annual quota.

## 5. Saved data and updates

Normal macOS launcher data lives in:

```text
~/Library/Application Support/SMAStockAnalyzer
```

The market_data.sqlite3 and saved_lines.sqlite3 files survive relaunches and new
source ZIPs. Back up the folder privately while the app is closed. Do not post
it to GitHub or chat. An explicit SMA_ANALYZER_DATA_DIR overrides this location.
The launcher only migrates old folder-local data if the persistent destination
does not already exist; it never overwrites that destination with an old copy.

To update, download/extract main again and launch the new folder. Keep the old
folder/backup until the new app opens correctly. Clearing downloaded market data
keeps saved parameters; deleting the persistent folder removes local state.

Desktop requests run at startup or on user actions only. There is no closed-app
price scheduler or desktop notification delivery. Phone notification settings
are preserved but delivery/background tests belong to Android.

## Optional diagnostics

After closing the app:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m scripts.smoke_yahoo_ui
.venv/bin/python -m scripts.check_yahoo --query Apple --symbol AAPL
```

Unit/UI fixtures do not call the live provider; check_yahoo explicitly does.
Some host packaging checks require requirements-validation.txt. The explicit
`bash run-desktop.command --demo` route uses separate fictional data/storage.

## Troubleshooting

- If macOS/security software blocks a file, retain the block and report the
  exact filename, wording and OS version. Do not disable protection or remove
  quarantine flags as a workaround. The isolated Yahoo helper prevents its
  failure from closing the Kivy window; it does not establish a false positive.
- For installation certificate errors, use the Python 3.12 installer's
  Install Certificates.command, then retry. Do not disable TLS verification.
- If a file cannot be found, repeat the cd step with the newly unzipped folder.
- Copy the final Terminal error and command, or the app request log. A network
  warning must not delete usable saved charts. [Desktop testing](docs/YAHOO_DESKTOP_TESTING.md).
