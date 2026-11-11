# Independent frequency-policy reference

This is a retained **date-free research/test reference**, not the current live
annualization specification. Live app rules are in
[the 365-day policy](CALENDAR_YEAR_FREQUENCY.md) and [app summary](../APP_SUMMARY.md).

[experiments/observable_frequency.py](../experiments/observable_frequency.py)
implements the independent baseline used by
[its regression tests](../tests/test_observable_frequency_experiment.py).
The tests compare exhaustive candidate selection, rolling averages, below/equal/
above events, warm-up/gap handling, history-dependent caps and coverage failures.
Keeping this reference independent helps catch arithmetic drift in optimized code.

The baseline has no actual session dates and annualizes with 252 trading
observations. Production live callers supply real dates and use 365 calendar
days, including weekends/holidays between usable adjacent observations.
The trading-observation cap in [policy.py](../sma_analyzer/policy.py) does not
change that live annualization definition.

```sh
python -m unittest tests.test_observable_frequency_experiment -v
```

Earlier proposals, example tables and discussions are in Git history. Do not
reapply their date-free annualization to live histories.
