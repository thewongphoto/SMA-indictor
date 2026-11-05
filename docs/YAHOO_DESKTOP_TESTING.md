# Private Yahoo desktop test

This iteration adds Yahoo EOD retrieval to the approved Kivy screens. It makes
requests on launch or user interaction only. It does **not** run a background
worker, deliver desktop notifications or start an APK build.

Live mode starts with **Choose a company**, not DEMO SGX. Its library and archive
list only Yahoo saved parameters; older synthetic saves are preserved separately.
The launcher always selects Yahoo unless --demo or --smoke-test is passed
explicitly. A failed Yahoo download does not generate substitute sample prices.

Use [START_HERE_MAC.md](../START_HERE_MAC.md) to download main and launch with
Python 3.12. The launcher installs requirements-desktop.txt, including yfinance
1.8.0. No Yahoo account/API key is normally needed for these public-data calls.

## What to test

| Action | Expected data operation |
| --- | --- |
| Start a new app process | One small SPY five-day history check; successful startup stays quiet. Failure adds a nonblocking Library warning. |
| Type Apple, AAPL, DBS or D05.SI | No request until Enter or Submit. |
| Submit a new query | One Search operation. US/SG stocks and ETFs only. Company logos use packaged assets or initials. |
| Submit that query again | Cached results, zero calls. Refresh search results explicitly repeats the search. |
| Select a security for the first time | One full available daily-history operation, period=max. Yahoo can add cookie/crumb/timezone requests internally. |
| Select/View it again while fresh | Read persisted history, zero history calls. Saved View opens its exact SMA period. |
| Open a stale security after its update target | One incremental history operation, normally overlapping ten calendar days. Cached saved charts can open while the request waits. |
| Change SMA frequency, chart range, inspect/zoom, save/hide, or change the backtest period | Local calculations, zero additional API calls. All saved SMAs for a security share its price history. |
| Settings → Refresh selected prices | Explicit incremental refresh, preserving the selected/saved SMA period. |
| Settings → Refresh all selected history | Full available history for the **selected security**, not every saved security. |
| Close the app window | No future scheduled API calls or notifications. An already-running request may finish before the process exits. |

In Settings, **View data request log** shows recent app-level operations and their
outcomes. Cached reads do not add API operations. Internal HTTP requests are not
counted individually. A corporate-action/adjustment change can cause one extra
full-history resynchronization after an incremental request.
Rows named history-result or health-result describe validation/cache outcomes,
not additional network operations.

## Search, charts and comparisons

1. New analysis → search → Enter/Submit → select a matching company.
2. On Parameters select a crossing frequency; Custom retains the numeric custom
   frequency. Fictional Trending/Oscillating/Sideways controls are absent for
   Yahoo securities.
3. Optimize. The calculation examines all available history; it does not limit
   MAX to five years or narrow the candidate grid. Long histories take longer.
   Close the window to cancel an active optimization.
4. Results shows company logo/name, actual dates, quotation currency, last close
   and refresh time. The chart and backtest use calendar-year windows on Yahoo
   data; MAX includes every downloaded completed daily bar.
5. Each comparison invests 100 units of the security's quotation currency per
   buy. USD and SGD quotations are supported; this is not an FX-converted portfolio.
   Yahoo Close is used with auto_adjust=False; Yahoo may still normalize for splits.
   Cash dividends, fees, taxes and slippage are excluded.
6. Crossing prices remain interpolated intersections of daily line segments.
   These are estimates using confirming EOD data, not observed intraday fills or
   a promise that a live trade could have obtained those prices.
7. Save two different SMA periods for the same security. View each from Library;
   each should retain its own exact period and both should share one cache.

The guided example and old preview saves remain synthetic, separate from Yahoo
identities. They do not use the live API. The local-demo screenshots and prior
preview guide describe that simulation mode rather than historical Yahoo prices.
Use `bash run-desktop.command --demo` to open the separate offline demo.

## Persistence and offline checks

On macOS the normal launcher uses:

    ~/Library/Application Support/SMAStockAnalyzer

Both market_data.sqlite3 and saved_lines.sqlite3 are retained between runs and
new ZIP downloads. An explicit SMA_ANALYZER_DATA_DIR overrides this location.
On Windows/Linux, the same shared path helper chooses the platform's persistent
application-data directory. Native mobile builds will supply their app-owned
persistent directory; they must not use disposable OS cache directories.

On first use, the launcher copies old .local/preview-data saves only if the new
destination does not yet exist. Close older app copies before migrating. If the
destination already exists, the launcher does not overwrite it. Keep the old
folder as a backup.

Test persistence:

1. Search, load a security, optimize and save.
2. Close the app normally and reopen it. Its saved company should be in Library.
3. Disconnect Wi-Fi and open the same saved SMA. The startup check may warn;
   the saved chart should remain available. A stale refresh failure must retain
   the old data and show its last close, not replace it with an empty chart.
4. Reconnect. Use Settings → Check Yahoo connection and Refresh selected prices.
5. Settings → Clear downloaded prices and search results asks for confirmation.
   It keeps company identities, saved parameters, preferences and unsaved-line
   history. Opening a Yahoo saved line afterwards downloads its history again.

Freshness never automatically deletes cached prices. Closing the app does not
clear anything. An OS uninstall/Clear storage or device loss can still remove
app files; copy the persistent folder while the app is closed for a manual private
backup. Do not upload that private cache to this repository.

## Error diagnosis and the cloud test limit

The desktop Yahoo transport now runs in a short-lived support process for each
operation. If a native dependency is blocked or crashes, the app keeps its window
open and reports that failure. The support process receives JSON parameters and
returns dated observations; no background daemon is created. Mobile builds use
their own transport adapters.
This contains a failure of the Yahoo support process. It cannot keep the GUI
running if the OS blocks the Python interpreter or Kivy itself.

If an OS/antivirus alert appears, its exact wording and named file are needed to
identify the cause. Do not assume a false positive or disable protection.
Process isolation is crash containment, not a cure for a quarantined/detected file.
The reported malware alert remains unconfirmed until its exact filename, wording
and OS/version are supplied; this update does not declare it a false positive.

Use the data request log first. The app distinguishes access blocking, rate
limiting, secure-connection failure and timeouts where possible. A failed request
does not prove a global Yahoo outage, and a successful SPY check does not prove
that every symbol or search request works.
Rate limiting pauses new requests for at least 60 seconds (longer when an exposed
Retry-After header requires it). That cooldown survives restarting the app;
cached queries and charts remain available.

For a Terminal diagnostic, from the project folder:

```sh
.venv/bin/python -m scripts.check_yahoo
.venv/bin/python -m scripts.check_yahoo --query Apple --symbol AAPL
```

The first command explicitly makes one availability operation. The second also
searches/loads the selected security, using persistent caches where applicable.
Use --refresh to repeat a cached query/history explicitly. Neither command
schedules work nor sends notifications.

In this implementation session the installed yfinance client was exercised, but
the cloud proxy rejected Yahoo access. The live startup probe correctly reported
access blocked and retained its cache. Automated adapter and running-widget
tests therefore use synthetic transport fixtures. **Successful live price
retrieval must still be confirmed on the owner's Mac/network.** A cloud policy
denial is not evidence that the Mac's Wi-Fi or Yahoo itself is offline.

## Deferred mobile work and schedules

The portable definitions in schedule.py record the requested Singapore times:

| Listing market | Future target, Asia/Singapore | Intended weekday close |
| --- | --- | --- |
| US stocks/ETFs | Tuesday–Saturday, 06:00 | Previous US weekday |
| Singapore stocks/ETFs | Monday–Friday, 17:30 | Same Singapore weekday |

For now these targets determine when an on-screen cached history is due for a
refresh. They do not trigger network work while the app is closed.

yfinance does not provide a dependable forward exchange-holiday calendar for
arbitrary markets/dates. A missing bar is not proof of a holiday. The current
app retains the last supplied completed close; future work can add maintained
exchange schedules and handling of exceptional closures.

At the APK stage, implement native background scheduling/notification permission
and test Doze/sleep, background suspension, delayed execution and catch-up.
Android and iOS can delay or deny background work even if an app was not explicitly
force-stopped. An iOS UI cannot be assumed to keep executing Python indefinitely
after backgrounding. Target cross-platform data/job contracts now; validate each
native adapter separately. iPhone installation still needs a separate signed
iOS build; see [the private iPhone guide](PRIVATE_IPHONE_INSTALLATION.md).

## Automated verification

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m scripts.smoke_yahoo_ui
```

The second command opens a temporary Kivy test window, uses synthetic transport
fixtures and exits. It does not contact Yahoo or use your personal cache. The
existing smoke_ui script retains coverage of the previous demo/Android UI.

Verified for the startup follow-up on 5 November 2026: **142 unit tests**,
**6 library-flow groups** and **13 Yahoo UI groups** passed. The previous desktop
iteration also passed **46 existing UI groups**. Yahoo adapter/UI
validation uses controlled transport fixtures; the live probe exercised the
installed client and reported the cloud network access block described above.
The isolated dependency-import check loaded the installed yfinance 1.8.0.
The OS-kill UI check simulates a stopped helper; it does not diagnose the owner's
security product or verify a fix for its specific alert.
No successful live Yahoo retrieval, physical-phone background execution or
notification delivery is claimed by these results.
