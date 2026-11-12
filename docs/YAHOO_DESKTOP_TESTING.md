# Desktop data and persistence testing

Current source: **0.13.5**. [Start on a Mac](../START_HERE_MAC.md), or install
requirements-desktop.txt in a Python 3.12 virtual environment. Live mode uses
an isolated yfinance helper so a blocked/crashing native dependency reports a
failure instead of closing Kivy. Android uses the separate mobile HTTPS client.

The desktop scope is interactive retrieval/UI only: startup check, submitted
search, selection/saved View when needed and explicit refreshes. Closing the
window does not schedule future API work or desktop alerts. An already-running
request can finish before process exit.

## Expected operations

| Action | Expected behaviour |
| --- | --- |
| Start a provider/app lifetime | Small VOO availability check; success stays quiet and failure adds a nonblocking Library warning. |
| Type / submit search | No request while typing; Enter/Submit searches once and persists results. |
| First selection | Full available completed daily history, not a five-year MAX cap. |
| Fresh saved View | Persisted history, exact saved period and no reoptimization. |
| Stale open / explicit refresh | Incremental history; a revision/adjustment change can require one full resync. |
| Range / pinch / backtest / save / rename / colour | Local data/calculations, no new market request. |
| Close window | No future scheduled fetches or desktop notification delivery. |

[The market-data guide](MARKET_DATA.md) describes cache policy and wire/logical
request distinctions. yfinance can issue supporting session/timezone requests;
its desktop log does not individually count every internal wire call.

## Prices and calculations

Every live analysis, guide and return comparison uses complete **Adj Close**
values. Ordinary Close and actions are retained, not substituted when an
adjustment is missing. Corporate-action changes require consistent historical
resync. A bad refresh keeps a usable prior revision instead of erasing history.

Live frequencies/horizons use 365-day years, month views use calendar months,
and SMA periods remain trading observations. Full-history matching is independent
of chart zoom and backtest horizon. Saved periods/names/colours stay fixed.
Crossing entries are daily-segment intersections, not live execution prices.
Fees, taxes and FX movements are excluded. [Full rules](../APP_SUMMARY.md).

The guide always loads **Vanguard S&P 500 ETF (VOO)** independently of your
selected security. Its initial target is 4/year and investment horizon Max;
changing the horizon reuses its history/SMA. History can be longer than the
illustrative chart window. A failure never substitutes synthetic live prices.

## Test persistence and failures

1. Search, select, optimize and save; close and reopen. View exact saved lines.
2. Disconnect the network and View a cached saved SMA. A source warning can
   appear, but the chart and parameters remain. Reconnect and refresh.
3. Change a horizon, name or colour and check the log for zero extra calls.
4. Use Settings price refreshes. Refresh all selected history reloads only the
   selected security. Check the app/validation outcomes and stale-data message.
5. Explicitly clear downloaded data/searches and confirm saved parameters remain.

The Mac launcher's persistent folder is
`~/Library/Application Support/SMAStockAnalyzer`. Other desktop platforms use
the platform application-data path selected by paths.py. SMA_ANALYZER_DATA_DIR
can override it. Back up the closed app's folder privately before migrations.
Do not overwrite a current database with an older one. Explicit demo mode uses
separate synthetic data and leaves live saves separate.

## Diagnose a failure

Settings → View data request log is copyable. Share the version, action, logical
request ID and failure/result rows. The log excludes secrets/raw responses.
A rate-limit cooldown survives restarts; obey Retry-After rather than repeatedly
clearing caches. No claim that a one-symbol probe diagnoses a provider-wide outage.

For an explicit live check:

```sh
.venv/bin/python -m scripts.check_yahoo --query Apple --symbol AAPL
```

For offline fixture/UI checks:

```sh
.venv/bin/python -m scripts.smoke_yahoo_ui
.venv/bin/python -m scripts.smoke_mobile_yahoo_ui
```

Keep any malware/security block in place until its exact file/message has been
investigated. Do not disable TLS, Gatekeeper or antivirus as a workaround.

[Android installation](ANDROID_APK_GUIDE.md) and
[scheduled phone alerts](ANDROID_DAILY_NOTIFICATIONS.md) are separate checks.
The [iPhone Vercel/PWA route](PRIVATE_IPHONE_INSTALLATION.md) still requires a web
frontend/backend implementation; these desktop tests do not deploy one.
