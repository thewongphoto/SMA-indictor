# Android 0.9.0: market data and UI test

This private test APK enables real Yahoo company search, daily history, MAX,
persistent caches, visible failures and a copyable diagnostic report.
It contains no scheduled background fetcher or notification-delivery tests.
The optional guided example uses the selected company's downloaded history, or
loads SPY when no security has been selected. Visible app labels are provider-neutral.

## Get the APK from GitHub

1. Sign in to your GitHub account and open
   [Build Android test APK](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml).
2. Open the run for tag **apk-v0.9.0** / version **0.9.0**. A queued/running
   workflow is not a finished APK. Wait for a green check.
3. Scroll to **Artifacts**, download **sma-android-test**, and extract the ZIP.
4. Tap the APK in Android Files/Downloads and install it over the existing app.
   The package/signing identity is preserved. If Android reports a signature
   mismatch, keep the existing app installed and report that error.
5. Open the app, tap the Settings gear and confirm **DATA CONNECTION · 0.9.0**.
   If it shows another version, you installed a different artifact.

The GitHub server builds the APK; your laptop can be closed while it runs.
If a build fails, open the red step and share its final error, or download the
artifact's android-build.log. Re-running an old run uses its original commit.
For a later source fix, request a new run on main or use the next release tag.

## First data test

1. Open **New analysis**. The app starts without a selected company or mock prices.
2. Type **Apple**, **AAPL**, **SPY**, **DBS** or **D05.SI**.
   Typing alone makes no request. Press Enter or Submit.
3. Select a matching company/ETF to download its available daily history.
   Results are restricted to supported US/Singapore stocks and ETFs.
4. Choose a crossing frequency, then Optimize SMA. MAX includes all downloaded
   completed daily history. Long histories take longer to optimize; the work
   runs off the UI thread and does not use a shorter hidden analysis window.
5. Check company name/logo, actual dates, last close and USD/SGD labels.
6. Save an SMA, then save another for the same company. Viewing them should
   retain their exact saved periods and share one downloaded history.

The opening SPY five-day check is quiet on success. Failure produces a Library
warning. A successful SPY check does not guarantee that every search/symbol works.
A failed download never generates substitute demo prices.

## Open and monitor the request log

1. Tap the **gear → Settings**.
2. Tap **View data request log**.
3. Read the newest entries first. **Swipe up/down inside the list** to browse
   calls. Times are Singapore time. **Load older calls** adds another 100 locally
   recorded entries; it does not make a data request.
4. **Refresh log (no API call)** reloads local log entries; it does not contact Yahoo.
5. Tap **Copy diagnostic report**, return to this chat and paste it. Copy includes
   the loaded entries, including older calls after you load them.

The report includes app version, platform, Python version, transport, selected
cached date range, operation/request IDs, HTTP status codes, durations and
endpoint purpose labels. The underlying event log is stored locally and survives restarting the app.
No report is sent automatically.

| Row | Meaning |
| --- | --- |
| APP started | A logical search/history/availability operation began. |
| HTTP ... 200 | An HTTPS request returned successfully. Its JSON still needs validation. |
| APP ok | The transport operation returned data; later validation/cache-result rows can still flag a problem. |
| CACHE ... cache_hit | Stored results/history were reused. **No HTTP request** was sent. |
| APP failed / history-result stale | The operation failed or failed validation. Previously downloaded prices remain available. |
| APP deferred | Rate limiting paused a new attempt; no HTTP request was sent for that attempt. |

APP start/end and associated HTTP rows share the first eight characters of a
request ID, so multiple rows do not automatically mean multiple user searches.
Cookie/crumb negotiation can require extra HTTP requests within one app action.
Desktop yfinance logs have app-level operations; this mobile transport additionally
records individual HTTP outcomes.

The report excludes cookies, authentication crumbs, HTTP headers, response
bodies, account credentials and device/file identifiers. It does contain your
search terms, tickers and selected history range; review it before sharing.

## What to send when something fails

Paste the diagnostic report and add:

- What you tapped, in order (for example, New analysis → Apple → Submit).
- The ticker, selected SMA frequency and chart/backtest period, if relevant.
- The visible error, and whether the app stayed open or closed.
- Your Android version and whether you were using Wi-Fi or mobile data.

If the app closed, reopen it and copy the log promptly: earlier entries remain
in the local database, with a new startup check added above them. If it cannot
open at all, send the version, last action and visible Android error first.
Do not clear storage or uninstall while diagnosing persistence problems.

## Interpreting common responses

| Result | What to do |
| --- | --- |
| 401 followed by cookie/crumb setup and an APP ok | Standard anonymous-session recovery; not necessarily a final failure. Only one recovery is attempted. |
| 404 from fc.yahoo.com during cookie setup | Can be normal; the log labels it. It is not a missing stock-price response. |
| 401 still failing, or 403 | Yahoo rejected access. Copy the report; the app does not bypass the restriction. |
| 429 | Wait. New calls pause for at least 60 seconds or the exposed Retry-After duration, whichever is longer. The cooldown survives restarting. |
| 5xx | Yahoo/server failure. Keep cached prices and report the action/log. |
| Timeout / secure connection error | Check device time/connectivity. Copy the report. Certificate verification remains enabled. |
| HTTP 200 but validation/history error | Copy the entire report. An empty/changed response, unsupported symbol, missing timezone or non-daily data can still be unusable. |

Do not repeatedly press Refresh after a rate limit or access rejection.
The error identifies availability from this device, not a confirmed global outage.

## Cache and offline checks

- Repeating a submitted query uses its persistent result. **Refresh search
  results** explicitly repeats the network search.
- Reopening a fresh cached saved SMA should show CACHE and no new history HTTP
  call. Every cold app launch still makes one small availability operation.
- When a viewed history is due for an update, fetch only the missing/recent
  range, with a ten-day overlap. New splits, dividends or revised prices can
  require an additional full-history resynchronization.
- Settings → Refresh selected prices forces an incremental fetch. Refresh all
  selected history reloads that security's full history.
- Close/reopen, then test with airplane mode after saving a real SMA. Cached
  charts must remain. Reconnect and explicitly check/refresh again.
- Clear downloaded prices and search results asks for confirmation and retains
  saved SMA parameters, company identities and preferences. It does not clear
  the request log. Android Clear storage/uninstall can erase app-owned data.

Older simulated saves are retained in storage but excluded from the Yahoo
library/archive, so fictional lines cannot be interpreted as real investments.
Return comparisons contribute USD 100 per buy and use quotation-price returns,
estimated daily-line crossing fills and no cash dividends/fees/taxes or currency
movements. They do not include historical FX conversion.

## Check the UI refinements

- Cold-launch the app with two companies saved. Both should start collapsed.
- Save two different SMA periods for one company. Switch View between them:
  the first keeps amber and the next keeps its own color. Restart and check again.
- Choose an already analyzed target and tap Optimize. Its cached analysis should
  open immediately; a saved target uses its exact saved period. New daily prices
  invalidate unsaved analysis results, while saved periods remain fixed.
- Pinch slowly with two fingers. Spread to zoom in and bring them together to
  zoom out. Small movements should produce small range changes; lifting one
  finger should preserve the view. One finger still inspects EOD points.
- Check month/year labels on shorter ranges and spaced year labels on Max.
- Use the magnifier-plus to choose another security. Settings is top-right on
  all pages; Saved SMAs opens without a hamburger icon.
- In backtesting, verify total contributed equals crossings × USD 100. A's
  arrow/percentage compares ending value to contributions. B/C remain relative
  to A. A loss displays a red downward arrow; zero buys display N/A.

## Transport and platform scope

The Android/iOS-compatible adapter calls the same Yahoo search/chart service
routes used by the relevant yfinance methods. It parses their JSON into the
same provider/cache contract. **The APK does not embed the desktop Python
yfinance/pandas/curl_cffi stack** and never launches the desktop helper process.
This is a disclosed transport change, not an additional data provider.

The APK packages requests plus its HTTPS dependencies and tzdata. Yahoo access
is unofficial and can be denied or change. There is no API key, fixed guaranteed
quota or service-level guarantee. Data rights and private-use scope are unchanged.
The Mac malware alert remains a separate unresolved issue.

The existing Singapore schedule definitions are retained for future native
work: US Tue–Sat 06:00 SGT; Singapore Mon–Fri 17:30 SGT. They currently control
on-screen cache freshness only. This build does not trigger new API calls while
closed, schedule notifications, infer holidays from missing bars, or guarantee
execution during phone sleep. iPhone packaging still needs its own signed build.

## Validation limits

Local unit/UI tests use controlled JSON transport fixtures and verify parsing,
real-date semantics, cache migrations, errors, rate limiting, redaction and
copyable reports. CI runs those checks before packaging.
The cloud network blocks live Yahoo destinations, so successful retrieval and
native Android behavior must be confirmed on the physical phone after installing
the APK. A pushed tag is a build request, not proof of a successful APK.
