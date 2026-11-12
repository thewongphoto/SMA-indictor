# Android data, cache and request-log testing

Current source: **0.13.5**. [Install the matching successful APK](ANDROID_APK_GUIDE.md)
first. Prices are real completed daily histories for supported US/SG stocks
and ETFs. Android uses the portable HTTPS adapter; it does not bundle desktop
yfinance/pandas/curl_cffi. The feed remains for private personal use.

## Basic test

1. Start the app. One small VOO availability check runs; a failure shows a
   nonblocking warning while cached saved data remains usable.
2. New analysis → type Apple, AAPL, VOO, DBS or D05.SI. Typing makes no request.
3. Press Enter/Submit, then choose a logo/ticker/name match. The same page
   reveals target preferences after selection. First selection loads available
   completed daily history; MAX is not capped at five years.
4. Optimize and save two SMAs for a security. View each and confirm its own
   period, custom name, colour and preferences remain fixed.
5. Change chart/backtest ranges, pinch, inspect, rename and recolour. These
   actions reuse data rather than making market requests.
6. Settings → Refresh selected prices requests an incremental update.
   Refresh all selected history reloads **that selected security's** full history,
   not every saved security.

Charts, signals, guide and returns use **Adj Close**, including dividends and
splits. Corporate-action revisions may require a full-history resync. Missing
adjustments never silently use ordinary Close. [Data policy](MARKET_DATA.md).

## Check persistence

Save, close/relaunch and view a saved line. All company groups start collapsed.
Reusing fresh history/searches should show CACHE rows. Temporarily go offline:
the startup warning must not erase downloaded charts or saved parameters.
Reconnect and refresh. Clear downloaded prices/search results only through its
confirmation action; saved SMA parameters remain. Android app-storage clearing
or uninstalling is a different, destructive operation.

## Read and report the log

Open **Settings → View data request log**. Scroll through the entries and use
**Load older calls** where offered. Copy the report into the issue/chat.
Logs persist across normal restarts and market-cache clearing.

| Row | Meaning |
| --- | --- |
| APP started/ok/failed | Logical search/history/health operation; start and outcome share an ID. |
| HTTP | Actual mobile wire request and status/duration; not another UI action. |
| CACHE | Local reuse, with no network request. |
| history-result / health-result | Validation/cache outcome, not an extra HTTP call. |
| notification-* | Scheduling, SMA/signal checks, triggers, suppression, tests and delivery results. |

Share the report header, app version, last action, relevant request IDs and
failure/notification rows. Tokens, cookies, headers, raw responses and private
paths are excluded. Do not send databases, signing keys or account credentials.

| Failure | Next check |
| --- | --- |
| 401/403 | Provider access/session restrictions or network policy; do not disable TLS. |
| 429 | Respect the logged cooldown/Retry-After; it persists through restarts. |
| Timeout/connection failure | Retry after connectivity recovers; retain cached data. |
| No valid adjusted history | Inspect validation result and retry a full selected-history refresh. |
| No expected session close | Market freshness/holiday handling; missing data alone is not proof of a holiday. |

## Current UI checks

- 3M/6M/9M/1Y/3Y/5Y/Max, fractional pinch, nearest-EOD tooltip and no label overlap.
- Visible endpoint currency/% changes, matching direction arrows and full date
  ranges after pinch. Flat/empty states remain neutral.
- Twelve centred colour choices stay tied to each SMA, including after restore.
- The VOO guide starts at 4/year and Max and keeps your selected security intact.
- The correct upward-crossing logo appears at launch and draws repeatedly while
  calculating. Native Back cancels; matching saved/cached targets open immediately.
- Every saved-SMA menu groups companies and their lines consistently; restart
  leaves all groups collapsed. Settings remains top-right on every screen.

## Notifications and verification limits

New line switches and all three types default On; existing Off choices remain
Off. [The notification guide](ANDROID_DAILY_NOTIFICATIONS.md) defines conditions,
SGT schedules and the manual/background-path tests. Phone OS settings govern
banner/sound presentation. A local acceptance record does not prove a user saw it.

Fixture unit/UI checks, a successful native build and physical-phone behaviour
are separate evidence. [Current validation status](ANDROID_TEST_STATUS.md).
