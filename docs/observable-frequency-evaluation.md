# Observable-frequency proposal: pre-integration evaluation record

The policy conditions, interpretation limits, and current implementation status
are recorded together in [the app summary](../APP_SUMMARY.md).

This report records the experiment run **before** production integration. At
that time, the application was deliberately left unchanged. The agreed policy
is now active in the app: see [the current summary](../APP_SUMMARY.md). The mock
history still contains 252 sessions. Historical references to the "current app"
below mean the app version at the time of this evaluation.

## Tested rules

- Annual frequency = crossings × 252 / observable comparisons.
- Complete history of H sessions and SMA N has H-N usable comparisons. The
  first valid SMA is a baseline, not a crossing opportunity.
- Missing values, their surrounding invalid comparisons, and SMA re-warm-up
  are excluded. Equal-to-SMA observations remain usable exposure.
- Through 756 sessions, proposed cap = min(floor(H/2), 252). Above 756 sessions,
  proposed cap = H-504. Candidates start at period 2, as in the current app.
- Require actual observable comparisons ≥ H-cap, so gaps cannot silently
  undermine the coverage guarantee. Insufficient valid coverage is an error.
- Minimize absolute annual-frequency error, not raw crossing-count error.
  Exact rational ties choose the shorter period.

## Executed checks

**36 tests passed, 0 failed, 0 skipped:** 21 existing tests plus 15 proposal
acceptance tests. These cover hand-calculated SMA/crossing examples, off-by-one
warm-up exposure, 36 crossings over three observable years, unequal-duration
scoring, deterministic ties, missing data, equality, nonfinite values, invalid
input, insufficient coverage, cap boundaries and monotonicity, all six mock
datasets, and preservation of the current app optimizer.

The comparison runner also evaluated 18 current-data cases (six datasets ×
three targets) and eight longer-history boundary cases. It fingerprinted every
`sma_analyzer/*.py` file before and after to confirm no application source
changed. Longer fixtures were temporary research inputs; the UI data length
was not changed. No UI integration or new Android/device validation was done.

## Current 252-session simulations: proposed policy

All rows use a proposed cap of 126; rates are annualized from the usable
comparisons, not from all 252 input sessions. Actual crossing counts are shown.

| Fictional counter | Scenario | Target/year | SMA | Crossings | Usable comparisons | Actual/year |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| DEMO-SGX | Trending | 12 | 11 | 13 | 241 | 13.5934 |
| DEMO-SGX | Trending | 6 | 15 | 6 | 237 | 6.3797 |
| DEMO-SGX | Trending | 1 | 20 | 1 | 232 | 1.0862 |
| DEMO-SGX | Oscillating | 12 | 42 | 10 | 210 | 12.0000 |
| DEMO-SGX | Oscillating | 6 | 101 | 7 | 151 | 11.6821 |
| DEMO-SGX | Oscillating | 1 | 101 | 7 | 151 | 11.6821 |
| DEMO-SGX | Sideways | 12 | 22 | 33 | 230 | 36.1565 |
| DEMO-SGX | Sideways | 6 | 22 | 33 | 230 | 36.1565 |
| DEMO-SGX | Sideways | 1 | 22 | 33 | 230 | 36.1565 |
| DEMO-US | Trending | 12 | 11 | 11 | 241 | 11.5021 |
| DEMO-US | Trending | 6 | 13 | 6 | 239 | 6.3264 |
| DEMO-US | Trending | 1 | 15 | 1 | 237 | 1.0633 |
| DEMO-US | Oscillating | 12 | 42 | 10 | 210 | 12.0000 |
| DEMO-US | Oscillating | 6 | 100 | 7 | 152 | 11.6053 |
| DEMO-US | Oscillating | 1 | 100 | 7 | 152 | 11.6053 |
| DEMO-US | Sideways | 12 | 51 | 19 | 201 | 23.8209 |
| DEMO-US | Sideways | 6 | 51 | 19 | 201 | 23.8209 |
| DEMO-US | Sideways | 1 | 51 | 19 | 201 | 23.8209 |

A target is not guaranteed to be attainable. In particular, the same candidate
can legitimately win for 12, 6, and 1 if every candidate produces a higher rate.
These are simulated-data results, not profitability or future-frequency claims.

## Why both normalization and coverage matter

For DEMO-SGX Sideways, target 12:

- Current app: SMA 192, 12 crossings, displayed 12/year using the entire
  252-session denominator. It has only 60 observable comparisons; that same
  SMA would have a warm-up-adjusted rate of 50.4/year.
- Changing annualization alone, while retaining all current candidates, selects
  SMA 251: zero crossings over just one usable comparison. Its error of 12/year
  is smaller than the error of any higher-frequency candidate. This is not
  sufficient evidence of a rare-crossing SMA.
- The complete proposal requires at least 126 comparisons here. It selects
  SMA 22: 33 crossings / (230/252) = 36.1565/year. This is the closest eligible
  result, even though it is far from 12.

## Isolated boundary fixtures

The target is 12/year and each fixture is a longer seeded DEMO-SGX Sideways
simulation. These cases exercise the proposal only, not a new app default.

| Input sessions | Proposed cap | Minimum usable comparisons | Selected SMA | Crossings | Actual usable comparisons | Actual/year |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 503 | 251 | 252 | 251 | 29 | 252 | 29.0000 |
| 504 | 252 | 252 | 251 | 29 | 253 | 28.8854 |
| 505 | 252 | 253 | 251 | 29 | 254 | 28.7717 |
| 755 | 252 | 503 | 217 | 65 | 538 | 30.4461 |
| 756 | 252 | 504 | 217 | 65 | 539 | 30.3896 |
| 757 | 253 | 504 | 217 | 65 | 540 | 30.3333 |
| 1008 | 504 | 504 | 254 | 93 | 754 | 31.0822 |
| 1260 | 756 | 504 | 254 | 125 | 1006 | 31.3121 |

The cap grows from 252 at session 756 to 253 at session 757; it does not
shrink at the three-year boundary. Above three years, selected candidates
must retain at least 504 actual observable comparisons.

## Reproduce

From the project root, using Python 3.12:

```sh
python -m unittest discover -s tests -v
python -m experiments.evaluate_frequency --output artifacts/frequency-evaluation.json
```

These commands need only the Python standard library. The runner now verifies
that the active engine agrees with the independent reference implementation;
it also retains an uncapped normalization-only diagnostic. Its source fingerprints
verify that running the comparison itself does not mutate application files.
The app does not import the research reference. Current validation is 39 unit
tests and 14 running UI smoke groups; see the summary for active behavior.
