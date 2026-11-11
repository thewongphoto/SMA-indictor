# Market data and persistent caching

The current application uses Yahoo data privately. Desktop requests use an
isolated yfinance helper. Android uses the compatible HTTPS search/chart
subset directly, without desktop pandas/curl_cffi dependencies. Neither is an
official Yahoo SLA-backed API. Actual limits/provider restrictions can change;
the app respects failures and rate-limit cooldowns instead of promising a quota.

| Operation | Trigger and reuse |
| --- | --- |
| Availability | One small VOO five-day history check per provider lifetime; explicit Settings retry is separate. Failure warns without deleting cached charts. This probes a real request, not a service-wide status endpoint. |
| Search | Enter/Submit only. Persist normalized query results; reuse until explicitly cleared/refreshed through supported actions. |
| History | First selection loads all available completed daily bars. A fresh saved View reuses persistent history. |
| Stale refresh | On an eligible interactive open/explicit refresh or enabled Android daily job; incremental requests overlap recent calendar days. |
| Revision | Changed corporate actions/adjustments or identity metadata require a full-history resync. Invalid/incomplete refreshes preserve usable prior data. |
| Local actions | Optimize, chart ranges/pinch/inspection, backtest horizons, save/name/colour/hide and archived restore do not themselves fetch prices. |

All SMAs for a security share one history. Mobile wire requests are separately
logged from logical app operations; yfinance may make supporting session/timezone
requests internally. A result/cache row is not another provider call.

Store and analyse dividend/split-adjusted daily closes, preserving ordinary Close,
actions, dates, exchange timezone and currency for validation. Never replace a
missing adjustment with ordinary Close or add dividends to adjusted returns.
MAX includes older available history. [Calculation rules](../APP_SUMMARY.md).

SQLite state survives closing and reopening. Explicit market-cache clearing
keeps saved parameters. App uninstallation/OS app-data clearing can delete the
whole local store. Desktop backup paths are in the [desktop guide](YAHOO_DESKTOP_TESTING.md).
Logs exclude cookies, tokens, headers, raw responses and private paths.

US/SG weekdays and update targets are freshness hints, not a complete holiday
calendar or an intraday feed. Missing expected closes must be reported/checked,
not relabelled as a known bank holiday. No upcoming-holiday discovery service
has been integrated. [Scheduled signal rules](ANDROID_DAILY_NOTIFICATIONS.md).

This remains private personal use. A future server-hosted web adapter must test
provider access from its deployed IPs and respect data permissions. Vercel
hosting does not turn the data into a public redistribution licence.

Source boundaries: [providers](../sma_analyzer/providers.py),
[history/cache policy](../sma_analyzer/yahoo.py),
[mobile transport](../sma_analyzer/mobile_yahoo.py),
[desktop transport](../sma_analyzer/desktop_yahoo.py) and
[persistent market cache](../sma_analyzer/market_cache.py).
