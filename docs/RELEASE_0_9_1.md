# 0.9.1 — dividend-inclusive prices

All live charts, SMA calculations/crossings, guided examples and backtests now
use the provider's **Adj Close**, including dividend and split adjustments.
This is the closing-price series returned by yfinance auto_adjust=True.
The desktop adapter requests auto_adjust=False to retain both Close and Adj Close
plus corporate actions in one operation; analysis selects Adj Close. Android's
portable JSON transport explicitly requests adjusted closes from the same service.

Backtest ending values use adjusted price ratios, approximating reinvested
dividends. Dividends are not separately added, avoiding double counting. The
USD contribution convention is unchanged; fees, taxes and currency movements
remain excluded. Crossing fills are still intersections of adjusted daily lines,
not observed intraday executions.

Complete adjusted values already on disk are reused without additional calls.
A legacy cache with missing/invalid adjustments requires a full download on
selection/View. Ordinary Close is never used as a fallback. A missing adjustment
or incomplete refresh is a visible failure and cannot replace a previously
complete adjusted revision. Corporate-action/revision detection resynchronizes
the full series so historical adjustment factors stay consistent.

Saved SMA periods, identities, visibility and colors are preserved. Their SMA
values and crossings are recalculated on adjusted history. Old unsaved optimizer
choices are invalidated by the updated price-basis fingerprint. The basis is
also included in the copyable diagnostic report.

Labels now say adjusted daily close and dividends included; the inspector
distinguishes adjusted closes from ordinary EOD quotations. Updated
[screenshots](design/ui-0.9/README.md) use controlled test responses.

Validation: 183 unit tests, including 11 adjustment/upgrade/return regressions.
Also passed 91 UI checks: 46 existing, 6 library flow, 13 desktop provider,
14 mobile transport and 12 live-screen/gesture refinement checks.
Live transport/UI tests deliberately provide different Close and Adj Close
series. Local checks use fixtures, not live market access. No dependency or
package/signing changes; background fetching and notifications remain deferred.
The `apk-v0.9.1` tag requests a new GitHub APK compilation; build completion must
be checked in Actions.
