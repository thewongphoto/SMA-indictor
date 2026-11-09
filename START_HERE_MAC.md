# Open the app on your Mac

The latest Kivy desktop preview is available on GitHub's **main** branch.
It now retrieves **Yahoo Finance EOD data for private testing**. These instructions
download and run that version; no Android APK build is needed.
See [Yahoo desktop testing](docs/YAHOO_DESKTOP_TESTING.md) for the API/cache checks.
For Android APK testing and request-log reporting, use
[Android Yahoo testing](docs/YAHOO_ANDROID_TESTING.md).
For installation on your own iPhone, use the separate
[free Mac/Xcode iPhone guide](docs/PRIVATE_IPHONE_INSTALLATION.md).

These instructions assume you have never used Python or Kivy. Python runs the
program; Kivy draws the app's screen. You do not need to edit any code.

## 1. Check Python

Open Terminal and run:

```sh
python3.12 --version
```

Use Python **3.12**. Your previously confirmed Python 3.12.10 is suitable.

## 2. Get the project from GitHub

1. Open <https://github.com/thewongphoto/SMA-indictor> in your Mac's browser.
2. Sign in to your own GitHub account if the repository is private.
3. Select the **main** branch if it is not already selected.
4. Click the green **Code** button, then **Download ZIP**.
5. In Finder, open **Downloads** and double-click the downloaded ZIP.
6. Open the extracted folder, normally called **SMA-indictor-main**. You should
   see `main.py`, `requirements.txt`, `run-desktop.command`, and this document.

If you already have an older download, extract the new one into a separate
folder and choose **Keep Both** if Finder asks. GitHub changes do not update
an existing ZIP download or the folder you extracted from it.

## 3. Open Terminal in the project folder

1. Press **Command + Space**, type **Terminal**, and press **Return**.
2. Type `cd` followed by one space. Do not press Return yet.
3. Drag the newly extracted **SMA-indictor-main** folder from Finder into Terminal.
   This inserts the folder's path for you.
4. Press **Return**. Terminal is ready to run commands in that folder.

## 4. Prepare and open the app

Copy this line into Terminal and press Return:

```sh
bash run-desktop.command
```

The launcher creates `.venv` if needed, installs Kivy, yfinance and the other desktop
requirements, then opens a window titled **SMA Stock Analyzer**. The first launch
needs internet access to download dependencies. It makes a small Yahoo
availability check; search and selecting a match download market data as needed.
No Yahoo account/API key is normally required. Leave Terminal open while you use the app.
The normal command always selects Yahoo mode. Simulation requires the separate
`bash run-desktop.command --demo` command.

Saved SMAs and downloaded data now persist in
`~/Library/Application Support/SMAStockAnalyzer`. Closing the app and downloading
a newer ZIP do not clear them. The launcher copies older folder-local preview
saves only if that persistent destination does not already exist; it never
overwrites an existing destination. Close older app copies first.

## 5. Try the desktop preview

1. The app opens on **My SMA library**. If you have saved Yahoo SMAs, their company
   groups appear immediately. Otherwise **New analysis** comes first.
   No DEMO SGX security or fictional prices are selected in live mode.
   Older simulated saves remain stored separately and do not appear in the
   Yahoo library. Click **New analysis**, enter a partial ticker/company name in
   **Search security** (for example `Apple` or `DBS`),
   then press Enter or **Submit**. Click a logo/ticker/name match to load its
   Yahoo daily history. Typing alone never searches or changes the security.
   Try `AAPL`, `VOO`, `SPY`, or `D05.SI`; search supports US/SG stocks and ETFs.
2. After selection, the same screen changes its heading to **Set your preference**
   and reveals the target/Optimize group with a short downward animation. Choose
   **12** crossings per year, then click **Optimize SMA**.
   Custom supports another numeric frequency. Fictional patterns are not offered
   for Yahoo prices. The app moves to Results; MAX includes all available
   completed daily history, which can take longer to analyze.
3. Plus markers show estimated price/SMA intersections. Drag the mouse across
   the chart to inspect the nearest EOD date, price, and SMA value; this does
   not zoom. Use **3M**, **6M**, **9M**, **1Y**, **3Y**, **5Y**, or **Max** for quick views. Two-finger
   zoom requires an input device/provider that supplies two touches to Kivy;
   a normal laptop mouse supplies one pointer. **Zoom out** restores a preset.
4. Scroll to section **03 / Backtesting**. Its independent period dropdown sits
   beside **If you invested USD 100 per buy for the past:**. Each scenario buys N times:
   a at upward crossings, b at equal-period starts (DCA), and c using the most
   common whole-dollar average-price group among 500 random samples. Each
   purchase contributes USD 100 to a dividend-adjusted return comparison; currency movements
   are excluded. The total contributed appears above the scenarios. Ending
   values show a's percentage growth against that contribution, and b/c
   percentage differences relative to a. Click either circled **i** for help.
5. Click the outline heart in the Optimal SMA card to save a line. Try another
   target or security, optimize, and save again.
   The pencil beside a saved line's session count opens **Name saved SMA**.
   Its custom name appears on the chart, saved menus, backtest and crossing
   details. Clearing the name restores its default. The selected target stays
   beside the name, with the session count retained below a custom name.
6. Open **Saved SMAs** with the top menu. Click the down arrow beside
   a security to expand its saved SMA rows; click the up arrow to collapse them.
   Headers show the logo, company name and ticker. A soft rounded background
   groups each expanded company with its SMAs. Long names shorten at a whole
   word while the ticker stays visible.
   Every company starts collapsed on each fresh launch. SMA colors remain tied
   to their periods within each company, even when another line is selected.
   The magnifier-plus at the chart's top left opens **Choose a security**;
   Settings stays at the top right on every page.
   Each row has View, Hide/Show, heart, and notification controls. The saved
   library on the launch page uses the same groups and shares their expanded state.
7. Click **View** to open a saved line's exact parameters. **Change parameters**
   returns to the selected stage of the merged search/preferences screen. The backtesting panel's **View all upward crossings**
   button opens the full event list; its Back arrow returns to Results.

Results use actual dates and show quotation currency, adjusted close and fetch time.
Live charts, SMAs, comparisons and the guided example use **Adj Close**, including
dividend and split adjustments. Returns approximate reinvested dividends; fees,
taxes and currency movements are excluded. Dividends are not added a second time.
Crossing prices are interpolated from adjusted daily segments, not observed
intraday trades. The SMA optimizer matches crossing frequency rather than
maximizing returns. See the Yahoo testing guide for cache behavior and API limits.

Close the window when finished. On later visits, repeat step 3 and run
`bash run-desktop.command` again. That reuses this copy's environment and saves.

## Test the API and persistent cache

Use the gear to open **Settings**. Check Yahoo connection explicitly retries the
startup check. Refresh selected prices updates the current security; Refresh all
selected history reloads its full history. View data request log shows the
requests and outcomes. Reusing a cached query/security should not add requests.

Save a Yahoo SMA, close and reopen the app, then temporarily disconnect Wi-Fi
and View that saved SMA. A connection warning must not erase its chart. Reconnect
and refresh. Clear downloaded prices and search results asks for confirmation
and keeps the saved SMA parameters.

Desktop has no background fetcher or notification delivery. Android 0.10.0 adds
native daily checks; use [the phone guide](docs/ANDROID_DAILY_NOTIFICATIONS.md).
Notification preferences are retained for the mobile stage. This version does
not call Yahoo on a schedule after you close the window or start an APK build.
New saved SMAs and both phone signal types default to On; existing stored Off
choices remain Off. Notification delivery remains an Android test, with triggers
and results available in Settings → View data request log on the phone.
This UI update adds a moving indicator during optimization. Press Escape
to cancel and stay on the selected company/target. Saved or cached targets still
open immediately. See [UI motion and banner behavior](docs/UI_MOTION_AND_ALERTS.md).
The startup check uses VOO. The live guided example always uses **Vanguard S&P
500 ETF (VOO)** and leaves your selected company/analysis intact. It starts at
4 upward crossings/year and a Max investment horizon; both selectors can be
changed, with Custom years available for the horizon. On a saved
chart, use the palette icon left of the pencil to select one of 12 line colours.
DBS and recognized ETF providers use [bundled offline logos](docs/OFFLINE_LOGO_CATALOGUE.md).

To unsave a line, click its red heart. The history/clock icon in section 02 lets
you restore the last ten unsaved lines. Hide/Show only controls the chart line;
notification preferences are separate.

## Optional: run the tests

After closing the app, run this in the same Terminal folder:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Successful output ends with `OK`. For the Yahoo adapter's running-widget test:

```sh
.venv/bin/python -m scripts.smoke_yahoo_ui
```

That uses synthetic transport fixtures and a temporary database; it never calls
Yahoo. To explicitly test live connectivity in Terminal:

```sh
.venv/bin/python -m scripts.check_yahoo --query Apple --symbol AAPL
```

The result distinguishes a failed check from a successful data download.
For the focused running-widget desktop checks, use:

```sh
bash run-desktop.command --smoke-test --preview-rules-only
bash run-desktop.command --smoke-test --library-flow-only
```

That uses a temporary test database and exits when the checks finish.

## Getting a newer version from GitHub

Download the ZIP again using step 2 and extract it to a new folder. Keep the old
folder until the new version opens successfully, then repeat steps 3–4.

The Yahoo launcher reuses the persistent Application Support directory across
downloads. Keep a private backup of that folder while the app is closed.
Do not overwrite an existing database with an older one. Older
`.local/preview-data` folders remain available as backups; automatic migration
only runs when the new destination does not exist.

Older desktop copies launched directly with `python main.py` used Kivy's per-user
application data directory; those files are not deleted or automatically moved
by this launcher.

## If something goes wrong

- **Malware/security alert:** keep the named file blocked. Paste the exact alert
  wording, filename and your OS/version so the blocked component can be identified.
  This update isolates the Yahoo libraries from the Kivy window, so a support
  process failure is shown in the app instead of closing its window. Isolation
  does not establish that an alert is a false positive or repair the blocked file.
  Do not disable antivirus, Gatekeeper or certificate checks, or remove quarantine
  flags as a workaround.

- **Certificate/SSL error during installation:** in Finder, open
  **Applications > Python 3.12**, double-click **Install Certificates.command**,
  let it finish, then retry the launcher command.
- **Cannot find run-desktop.command, requirements.txt or main.py:** repeat step 3
  using the newly downloaded folder that contains those files.
- **Other error:** copy the last few lines from Terminal into the chat, including
  the command you ran. There is no need to reinstall everything first.
