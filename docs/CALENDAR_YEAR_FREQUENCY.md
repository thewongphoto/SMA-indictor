# A year means 365 calendar days

The live app previously annualized crossings with **252 trading observations
per year**. That was an approximation to a civil year, rather than a calculation
from the actual elapsed dates.

Version **0.13.1** uses the actual closing-session dates and exactly
**365 calendar days**, including weekends and exchange holidays:

```text
observable calendar days = sum of elapsed days between usable adjacent closes
observable years = observable calendar days / 365
crossings per year = upward crossing count × 365 / observable calendar days
```

**X/year means a target historical annualized average.** The optimizer picks
the eligible SMA closest to that rate across its usable history. It does not
require exactly X crossings in each January–December calendar year, or promise
that rate in future. For example, six crossings over 730 observable calendar
days equal 3/year even if the crossings are unevenly distributed between years.

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
warm-up/gaps, exact calendar-objective selection, mobile/NumPy equivalence,
annual average versus per-year quota, and cache/saved-line preservation.

Install a successful **apk-v0.13.1** or **ios-v0.13.1** build to use the change
on a phone. Publishing source does not modify an already installed 0.13.0 app.
