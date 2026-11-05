# Yahoo Finance integration plan

**Implementation update, 5 November 2026:** interactive desktop search/history,
persistent cache, full-history MAX, real dates/currency and startup diagnostics
are implemented. See [the desktop testing guide](YAHOO_DESKTOP_TESTING.md) for
the current scope and validation limits. Android/iOS packaging, background
fetching and notification delivery testing remain deferred. The plan below
records the original design and includes work beyond this desktop iteration.

## Original planning snapshot (4 November 2026)

Reviewed 4 November 2026 against the current 0.7.0 app, the official yfinance
documentation sources, and the published yfinance **1.8.0** source distribution
(released 3 November 2026). **This is a plan, not an implemented data feed.**
The app still uses simulated prices.

Scope: private personal use on the owner's devices. **MAX must include all
available Yahoo history**, as requested. No APK release or runtime dependency
changes accompany this document. Private iPhone installation is covered in
[the iOS guide](PRIVATE_IPHONE_INSTALLATION.md).

## Recommendation

Use yfinance's **Search** and **Ticker.history** methods behind the existing
provider boundary. Persist the results in a separate on-device market-data
database. Calculate SMAs, crossings, the 500 random comparisons, DCA and ending
values locally. Keep the guided example synthetic and available offline.

yfinance is an independent Python library that calls Yahoo's web services; it is
not a Yahoo-supported developer API with a service guarantee. Its Apache software
license does not grant rights to Yahoo or exchange data. Its README describes the
data API as intended for personal use. This plan does not establish permission
for future public display, redistribution, or unrestricted retention. Revisit
applicable data terms before changing the private-use scope.

## Methods, results and call budget

In this table, a **call means one app-initiated yfinance operation**, not an exact
number of HTTP requests. Cookie/crumb setup, a cold symbol-timezone lookup,
internal recovery and exceptional metadata fallbacks can add HTTP requests.
Persist yfinance's supported cookie/timezone caches as well as our own prices.

| App purpose | Method / underlying route observed in 1.8.0 | What it supplies | Planned calls |
| --- | --- | --- | --- |
| Search after Enter/Submit | `yf.Search(query, ...).quotes`; query2 `/v1/finance/search` | Candidate symbols, company short/long names where available, exchange and instrument type. Results can be incomplete or ranked differently from the local preview catalogue. | **1** per uncached submitted normalized query, or an explicit Refresh results. **0** while typing, for a repeated cached query, or when reopening search. Constructor performs the search; reading `.quotes` adds no request. |
| First selection of a security | `yf.Ticker(symbol).history(period="max", interval="1d", ...)`; query2 `/v8/finance/chart/{symbol}` | All available daily OHLC, Close, Adj Close where supplied, volume, dividends and splits; actual dated observations. Available coverage varies by security. | **1** full-history operation per new security/cache namespace. Search does not also download history. All SMAs for that security share this dataset. |
| Keep cached history current | Same `history` method, with an inclusive `start` overlapping the last cached date and an exclusive `end` | New completed daily bars and recent corrections. | **0** for fresh cached data; normally **1** incremental operation per viewed stale security after an EOD update is due. No refresh for every saved SMA separately. |
| Identity and daily-session metadata | `ticker.get_history_metadata()` **on the same object after its successful history fetch** | Currency, exchange timezone, exchange identifiers, name where present and current daily-session bounds. Cache a selected set of fields. | Normally **0 additional network requests** after history. Calling before history can fetch a separate short history; avoid this. Accessing lazy `tradingPeriods`, including by converting the entire mapping to a dict, can trigger an intraday request; avoid that key. |
| Quiet startup source check | `yf.Ticker("SPY").history(period="5d", interval="1d", ...)`; same chart route | A small, recently traded sentinel series that exercises the price-data path. It is an availability check from this device, not an official Yahoo health endpoint. | **1** fresh operation per cold app launch, in the background. **0** when returning from Settings or resuming the same process. Quiet on success; failure message only on error. |
| Optional stock-only search alternative | `yf.Lookup(query).get_stock(count=10)`; query1 `/v1/finance/lookup` | Stock lookup results; a possible replacement if Search coverage proves unsuitable. | **0 initially**. If selected later, use **1 instead of Search**, not both for every submission. |
| Multiple-symbol download convenience | `yf.download(...)` or `yf.Tickers(...)` | Convenience wrappers for several securities. | **0 initially**. These do not turn many symbols into one Yahoo HTTP request. |
| Company logos | Existing packaged assets, otherwise initials | Preserves the approved logo/company-name UI without another data service. | **0 Yahoo calls**. The reviewed API does not provide a dependable general company-logo endpoint for this UI. |
| Calculation, chart and library actions | Local engine and persisted history | Optimization, 1Y/3Y/5Y/MAX, custom-year backtests, crosshair, pinch zoom, save/hide/heart, DCA, random comparisons and crossing list. | **0**, once history is cached. Phone alert checks may require the same daily refresh if history is stale; changing their preferences does not. |

`Ticker.info`, `fast_info`, financial statements, news, options, screeners and
streaming WebSockets are unnecessary for this release's UI. In particular,
`Market.status` reports market state, not whether Yahoo's data service is healthy.
Dividends/splits come with the history operation; do not fetch them separately.

Examples, excluding internal HTTP setup/recovery:

| User journey | App-initiated operations |
| --- | --- |
| Cold launch, uncached search, select a new security | **3:** startup check + search + full history |
| Cold launch, open a fresh cached security | **1:** startup check only |
| Cold launch, open one security after a daily update becomes due | **2:** startup check + incremental history |
| Save/view three SMA lines for that same security | **0 extra**; one shared history refresh if due |
| Select the same cached security using a new uncached search query | **1** search; history adds **0** if fresh |
| Change backtest from 1Y to MAX or Custom within available history | **0** |
| A split/correction requires rebuilding the cached historical price basis | **1 additional** full-history resynchronization when detected |

There is no documented guaranteed yfinance calls-per-minute/day allowance or SLA.
Do not treat unofficial rate-limit estimates as an entitlement. Coalesce duplicate
requests, serialize requests initially, respect throttling/Retry-After when
available, and back off after 429 responses. Never rotate identities or loop to
evade blocks. The budgets above describe normal operations, not guaranteed
wire-request totals.

## Request settings and price meaning

Suggested method usage for the first desktop adapter, not a complete adapter:

```python
import yfinance as yf

# Configure once when constructing the provider, not around concurrent requests.
yf.config.debug.hide_exceptions = False
yf.config.network.retries = 0
yf.set_tz_cache_location(persistent_yfinance_state_directory)

matches = yf.Search(
    query,
    max_results=10,
    news_count=0,
    lists_count=0,
    recommended=0,
    include_cb=False,
    include_nav_links=False,
    include_research=False,
    include_cultural_assets=False,
    timeout=10,
).quotes

ticker = yf.Ticker(selected_yahoo_symbol)
bars = ticker.history(
    period="max",
    interval="1d",
    auto_adjust=False,
    back_adjust=False,
    actions=True,
    repair=False,
    prepost=False,
    keepna=True,
    timeout=10,
)
# Validate bars, completion time, identity and coverage before committing to SQLite.
# Read only needed metadata fields; do not materialize every lazy metadata key.
metadata = ticker.get_history_metadata()
currency = metadata.get("currency")
timezone = metadata.get("exchangeTimezoneName")
```

The directory and selection/query variables above belong to the future adapter.
These operations are triggered separately by their respective UI actions.
In 1.8.0 the history `raise_errors` argument is deprecated in favor of the
configuration shown above. A successful HTTP response with invalid or empty
data still needs explicit handling.

Recommended initial price policy: store both Yahoo **Close** and **Adj Close**
when provided, use **Close** for the chart/SMA/price-return comparisons, and label
the policy. `auto_adjust=False` avoids yfinance's default dividend adjustment;
it does **not** establish that Close is the original unadjusted, as-traded price.
Yahoo may already normalize prices for splits. Preserve corporate actions and
the dataset revision, and resynchronize old prices when that basis changes.

Under this policy the ending values are price-only estimates, excluding cash
dividends, fees, taxes and slippage. Using Adj Close instead would represent a
different adjustment/return assumption and change the displayed historical prices.
Do not silently mix the two series.

Show the actual quotation currency. The initial proposal is **100 units of that
security's currency per buy** (e.g. USD 100 or SGD 100), with no FX conversion
endpoint. Correct for provider quotation units such as pence if those securities
are later supported. Do not present SGD prices as USD.

EOD data cannot establish when a live intraday SMA crossing occurred or its
executable price. The app's current crossing prices are intersections of straight
segments between daily observations. Retain an explicit simulation label for
these fills; they can use information only known at the confirming close and
are not an executable live-trading backtest.

## Startup check and failure behavior

Use one fresh `history(period="5d", interval="1d", auto_adjust=False,
actions=False, repair=False, timeout=6)` operation for SPY after showing the
local Library. Reuse the configured provider and persistent timezone/cookie
state. Do not serve this check from our saved price cache or an HTTP response
cache. With no historical `end`, the reviewed daily-history path makes a live
data request; retain that property in the adapter.

Five days can include the last trading session across weekends/holidays.
A closed market is normal. Require a structurally valid nonempty response,
but do not demand a bar dated today. The sentinel checks only its own price
route; it cannot guarantee that search, SGX symbols or every other security work.

On success, show no banner or notification. On failure, use a nonblocking message:

> Unable to retrieve Yahoo Finance data from this device. Showing saved data.

Show the cached security's last completed session and last successful refresh.
For an uncached security, explain that a connection is needed to load its history.
Classify device connectivity, timeout, 403/access block, 429/rate limit and
server/invalid-response errors where evidence permits. Do not label all failures
as a confirmed global Yahoo outage.

One launch check means one app-level attempt, with no automatic repeated probes
that launch. A user-requested Retry is separate. The transport may still perform
cookie/crumb negotiation or authentication recovery internally. A six-second
HTTP timeout is not a six-second overall deadline; timezone/authentication steps
can add time. Keep the UI responsive and ignore late results after a UI deadline.
Queue user history/search operations behind an in-flight check to avoid bursts.

## Persistent cache contract

- Put a dedicated SQLite market-data database in app-owned persistent files
  storage (Android app data / iOS Application Support), **not** an OS-disposable
  cache or temporary directory. Closing, force-stopping or restarting the app
  must not erase prices, identities, submitted searches or saved lines.
- Key price history by provider, canonical Yahoo symbol, exchange/identity,
  interval and adjustment/schema version. Store actual session dates, OHLC,
  Close/Adj Close, volume/actions where available, currency/timezone, coverage,
  last completed session, fetch timestamps and a dataset revision.
- Use one history series for every SMA saved for that security. Keep search
  results keyed by the exact normalized query and any filters. A cached prefix
  is not proof that a longer query's complete global result set is known.
- Retain cached searches until an explicit refresh/clear. Show when results were
  last fetched; Refresh results allows recovery from old names or an empty result.
  Do not require a network request to reopen a previously searched query.
- Treat freshness as permission to **refresh**, not permission to delete.
  After a daily close plus a configurable publication grace period, refresh
  only a security being opened/used. Start with one automatic attempt per symbol
  per exchange-local date when due; holidays may produce no new bar. No polling
  loop and no refresh of every saved symbol at app launch.
- For incremental history, overlap roughly 10 calendar days before the last
  cached session (or fetch the entire missing gap if longer). Merge by session
  date in a transaction. An `end` date is exclusive; choose bounds that include
  the latest completed session, then filter incomplete bars in exchange time.
  Do not invent prices for exchange holidays or replace missing prices with zero.
- Exclude the current in-progress daily bar. Persist the exchange timezone and
  needed daily-session metadata; allow publication delay. Unknown session
  completion must be handled conservatively rather than called EOD.
- A split, changed adjustment factors or a detected historical correction can
  require a new full-history fetch. A recent overlap cannot detect every older
  vendor revision: offer an explicit **Refresh all history** action.
- Errors, empty responses and interrupted downloads never erase valid cached
  history. Validate and commit atomically; retain the prior revision on failure.
- Preserve caches through app upgrades with schema migrations. Keep yfinance's
  own cookie/timezone state persistent too; expired authentication may renew
  independently of the market-data cache.
- Settings should offer a confirmed **Clear downloaded market data** action
  while keeping saved SMA parameters, visibility, preferences and unsaved-line
  archive. Clearing search results and resetting the entire app are distinct
  actions. Do not perform either silently.
- Device loss, Android Clear storage, uninstalling, or deleting an iOS app can
  remove app-owned files. Offer a private export/restore backup if the data must
  survive those actions. Persistence across app closure is not a backup.

## Required changes to this app

| Current behavior | Integration work |
| --- | --- |
| `PreviewMarketDataProvider.search/historical_data` uses a local catalogue and synthetic generator. | Add a Yahoo adapter plus a durable repository; keep network work off Kivy's UI thread and retain existing stale-result guards. Preserve Enter/Submit and history-on-selection boundaries. |
| Security resolution accepts only the fixed preview catalogue. | Persist dynamic identities from Yahoo search/history. Resolve Yahoo symbols, not guessed exchange-prefixed UI keys: examples to validate include `AAPL`, `D05.SI`, `O39.SI`, `U11.SI`, `C6L.SI`. Handle name changes and ambiguous instruments. |
| `Dataset.dates` fabricates weekdays starting 2021-01-04. | Introduce real dated observations with currency/timezone/source metadata. Never attach Yahoo prices to fictional dates. Preserve valid missing observations and do not infer a crossing across a known gap. |
| Preview and saved lines use a mock data version. | Separate mock and Yahoo saved identities/namespaces. Preserve the existing demo library and archive; do not silently reinterpret old mock lines as historical investments. |
| Custom offers Trending/Oscillating/Sideways patterns. | Keep patterns in Demo/Guide only. Live analysis retains the numeric custom frequency without applying synthetic patterns to market prices. |
| MAX currently means all 1,260 loaded synthetic sessions. | Fetch `period="max"` once; MAX means all available completed Yahoo daily history. Short listings may have less than 1/3/5 years. Show the actual simulated date range and history limitations. |
| Period presets currently use session-count approximations. | Use actual dates for calendar 1Y/3Y/5Y/Custom windows and equal-time DCA intervals. Map each interval start to the next eligible trading close. Retain SMA warm-up and equal eligibility rules; disclose when the requested window lacks coverage. |
| The optimizer searches a history-dependent range of candidate periods. | Full history expands both input size and the candidate cap. Benchmark and optimize this calculation, run it in a cancellable background worker and reduce rendering cost without dropping analytical observations. Do not silently cap history to five years. |
| Saved View restores exact parameters. | On data refresh, recalculate the saved SMA and statistics at its **saved period**; do not re-optimize it automatically. A fresh Optimize may find another period with more history. |
| Prices, comparisons and labels assume a synthetic dollar series. | Carry quotation currency/units through tooltips, rounded-dollar modal-price grouping and ending values. Keep a: crossing fills, b: equal-period DCA, c: modal group among 500 random samples, and existing ending-value/percentage rules. All comparisons share one dataset revision and eligible period. |
| Phone notification checks use manually initiated data. | Reuse the daily refresh when checking signals. Closed-app alerts require a separate native scheduling design; adding history calls does not create a reliable background service. |

Full-history optimization is a material performance issue: the current exhaustive
search revisits the series for each candidate, so the work can grow roughly
quadratically with history length. Keeping MAX complete is the requirement.
Do not promise equal latency to the five-year prototype or silently change
frequency/coverage rules. Validate tie-breaking and calculation equivalence when
improving the engine.

## Android feasibility and limits

Native Android code is not subject to browser CORS, and the app already requests
Internet permission. HTTPS, device connectivity, provider access controls and
rate limiting still apply. Data requests belong on background workers.

yfinance 1.8.0 brings pandas, NumPy, curl_cffi and other dependencies absent from
the current APK. Python-for-Android recipes and compatible native libraries must
be verified for the app's actual embedded Python and ARM64 target. A compatible
desktop wheel, or even a published Android wheel, is not by itself proof that
Buildozer can package it correctly.

The reviewed version has a plain-requests fallback and documents installation
without curl_cffi, but explicitly calls that fallback best-effort: Yahoo can
block or rate-limit it. It is a packaging experiment, not a reliability guarantee.
Keep TLS verification enabled; do not solve failures by bypassing certificates
or provider access controls. Expect increased APK size and build complexity.

Do a minimal Android dependency/import/search/history/cache build first, then
test on the physical phone before updating the main APK workflow. If direct
packaging is unsuitable, consider a **personal authenticated backend** to keep
the heavy library off the phone. That adds hosting, network and privacy work;
it is an optional architecture decision, not required for the desktop prototype.

No Yahoo developer API key is normally required for the public-data methods
listed here. yfinance manages its own cookie/crumb negotiation. Do not ask the
user to publish Yahoo passwords, cookies or tokens, and never commit fetched
market histories, private exports or credentials to this repository.

## What the owner needs to do

1. Keep this integration for private use for now; revisit data permissions before
   sharing a data-enabled app or datasets publicly. A public source-code plan
   does not require uploading personal cached histories.
2. Supply a short priority test list of SGX/US securities and confirm whether
   stocks alone or ETFs too should appear in search. The examples above are a
   suitable initial test set; coverage must be checked against actual responses.
3. Review the proposed **Close / price-only return** policy and **100 units of
   quotation currency** convention before implementation. MAX covering all
   available history is already confirmed.
4. For live tests in this cloud environment, enable the Yahoo destinations through
   the supported network configuration and publish that configuration to the
   environment. The active cloud policy currently permits package/GitHub access,
   but blocks the hosted yfinance reference and Yahoo destinations. Expected
   data hosts are `query1.finance.yahoo.com`, `query2.finance.yahoo.com` and
   authentication bootstrap hosts such as `fc.yahoo.com`; the library can also
   use `finance.yahoo.com`, `guce.yahoo.com` and `consent.yahoo.com` depending
   on the response. Review observed requests before adding further hosts.
   These cloud settings do not configure the Android phone's network.
5. Keep the existing desktop launch working, and make an Android device available
   for the dependency/build test. Check first-load, restart, airplane mode,
   exchange close, corporate actions and multiple SMAs sharing one cache.
6. Decide separately whether closed-app notifications and export/restore are
   needed in the first live-data version. Both need additional implementation;
   neither is provided merely by installing yfinance.
7. For a private iPhone version, use the [installation guide](PRIVATE_IPHONE_INSTALLATION.md):
   a Mac/Xcode and Apple signing setup are needed. Do not send signing passwords
   or account credentials in chat.

Suggested sequence: persistent schema and real-date migration → desktop Yahoo
adapter with recorded fixtures → Android packaging spike → UI/cache/failure
integration → calculation and offline/restart validation → separately authorized
APK release. Build the iOS target separately if wanted.

## Verification required before a data-enabled release

- Search submits once; typing, cached queries and reading result properties add
  no requests. Unsupported/ambiguous symbols do not overwrite another identity.
- Prices and identities survive close/restart and an app update. Offline use
  retains the library and cached charts; cache clear preserves saved parameters.
- One cold-launch probe, quiet success, useful failure message, throttling
  cooldown and no false global-outage claim.
- Full-history first load, inclusive/exclusive bounds, completed-bar filtering,
  currency/units, exchange dates, split/correction refresh and atomic rollback.
- Multiple saved periods share one price series. Refresh preserves saved
  periods; chart gestures and cached backtest changes make no network calls.
- Existing crossing, warm-up, gap, random-mode, DCA and percentage rules remain
  correct on real dates and long histories. Benchmark MAX and optimizer latency
  on the target phone before promising performance.
- Record app-level calls separately from observed HTTP requests. Do not log
  cookies, crumb values, authorization headers or personal cache contents.

## Sources and access limits

The hosted reference was blocked by this cloud's network policy. The official
GitHub documentation source and published PyPI source were accessible and were
used instead. No live Yahoo response or Android yfinance build was validated in
this documentation task.

- [yfinance API reference](https://ranaroussi.github.io/yfinance/reference/index.html)
  and its [official source](https://github.com/ranaroussi/yfinance/blob/main/doc/source/reference/index.rst).
- [Search and Lookup documentation source](https://github.com/ranaroussi/yfinance/blob/main/doc/source/reference/yfinance.search.rst).
- [History reference source](https://github.com/ranaroussi/yfinance/blob/main/doc/source/reference/yfinance.price_history.rst).
- [Published yfinance 1.8.0](https://pypi.org/project/yfinance/1.8.0/). Method defaults,
  routes, lazy metadata behavior and fallback behavior were checked against its
  published source distribution, with its SHA-256 verified against PyPI metadata.
- [Official search implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/search.py),
  [history implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py)
  and [cache implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/cache.py).
  These main-branch links can change after this review.
- [Installation without curl_cffi](https://github.com/ranaroussi/yfinance/blob/main/doc/source/advanced/install.rst)
  and [HTTP backend implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/_http.py).
- [yfinance README and personal-use notice](https://github.com/ranaroussi/yfinance#readme)
  and [software license](https://github.com/ranaroussi/yfinance/blob/main/LICENSE.txt).
