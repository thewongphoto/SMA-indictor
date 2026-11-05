# 0.8.0 — private Yahoo Android data test

Android now defaults to the real-company Yahoo provider. Search submits only on
Enter/Submit, selection loads full daily history, and prices/search results
persist between sessions. Saved SMAs share a security's cache and retain their
exact periods. Download failures retain prior history and display connection or
validation errors; there is no fallback to synthetic prices.

A portable HTTPS adapter implements the Yahoo search/chart subset used by
yfinance, replacing desktop-only native dependencies in the APK. The desktop
continues using its isolated yfinance transport. Daily dates, currency, corporate
actions, cache schema and analysis rules are shared across platforms.

Settings → View data request log now shows correlated app/HTTP/cache events,
status codes, timings and endpoint paths. Copy diagnostic report creates a
sanitized, pasteable report without authentication values or response bodies.
See [Android testing and error reporting](YAHOO_ANDROID_TESTING.md).

The portable optimizer scores candidates in one rolling pass each, preserving
reference arithmetic, gaps, equality and tie-breaking, then constructs the exact
winning SMA/events. This avoids repeated validation and full-array allocation on
phones without NumPy; MAX and candidate coverage are not truncated.

The original Android package and signing workflow remain unchanged. Only the
version/data feature and portable dependencies change. Notification delivery,
background scheduling, sleep behavior and exchange-calendar work remain deferred.
The Mac security alert is not declared resolved by this Android release.

Local validation: **160 unit tests**, **46 existing UI checks**,
**6 library-flow checks** and **14 mobile-transport UI checks** passed.
Mobile transport responses in automated tests are synthetic fixtures; these
results do not establish live connectivity or physical Android behavior.
The apk-v0.8.0 tag requests a separate GitHub Actions compilation/signing run.
