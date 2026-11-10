# A year means 365 calendar days

The live app previously annualized crossings with **252 trading observations
per year**. That was an approximation to a civil year, rather than a calculation
from the actual elapsed dates.

The source for **0.13.1** now uses the actual closing-session dates and exactly
**365 calendar days**, including weekends and exchange holidays:

```text
observable calendar days = sum of elapsed days between usable adjacent closes
observable years = observable calendar days / 365
crossings per year = upward crossing count × 365 / observable calendar days
```

Warm-up and genuinely missing-price/SMA intervals retain their existing
exclusions. Normal Friday-to-Monday observations contribute **three days**, not
one. Holidays between adjacent valid closes count too. A leap-day span is
measured as elapsed days and still normalized with 365, rather than changing the
definition of one year to 366.

Both the optimizer's target matching and the displayed annual frequency use
this definition, including the live VOO guide and reconstructed saved results.
The optional NumPy and pure Python mobile scorers use identical exact-rate tie
rules. Date-free legacy/demo fixtures retain their historical approximation;
the live UI always supplies actual dates.

Live **1Y/3Y/5Y** chart and investment horizons use **365/1095/1825 days**.
Custom investment years use the same 365-day basis. Month presets remain actual
calendar months. SMA **(X days)** still means X trading observations.

Saved SMA periods, names, colours, notification settings and histories are
preserved. Their actual annual frequencies are recalculated, without silently
retuning saved lines. Derived unsaved optimizer choices from the old policy are
invalidated; this does not clear downloaded prices or saved SMA parameters.

Validation includes leap-year/window boundaries, weekend and holiday time,
warm-up/gaps, exact calendar-objective selection, mobile/NumPy equivalence and
cache/saved-line preservation. Both 308-test suites passed (one desktop-only
check skipped in the mobile dependency environment).

This is a source update for the next build. It does not change an already
installed 0.13.0 APK or iPhone app, and no APK/iPhone build tag has been added
for this source update.
