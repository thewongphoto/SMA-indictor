"""Pure SMA and upward-crossing calculations, independent of Kivy and SQLite.

Every index represents one trading session, including missing observations.
An SMA needs N consecutive finite prices; gaps restart its warm-up. Equality
keeps the last strictly above/below side. A missing price or SMA resets that
side. Only a below -> above transition counts; the first valid side is a
baseline. Thus below, equal, equal, above counts once, and above, equal, above
does not count. No crossing is inferred over a missing observation.
"""
from collections import deque
from dataclasses import dataclass
import math
from numbers import Real
from typing import Iterable, Sequence

from .policy import annual_frequency, maximum_sma_period, observable_comparisons
from .settings import TRADING_SESSIONS_PER_YEAR

Price = float | None


def _prices(values: Iterable[Price]) -> list[Price]:
    result = []
    for value in values:
        if value is None:
            result.append(None)
        elif isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError("Prices must be numbers or missing values (None).")
        else:
            result.append(float(value) if math.isfinite(value) else None)
    return result


def _positive_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive whole number.")


def simple_moving_average(prices: Sequence[Price], period: int) -> list[Price]:
    """Return a same-length SMA, with None for warm-up and missing windows.

    A period longer than the history raises ValueError, including empty history.
    Period 1 is mathematically supported, but excluded from optimization because
    it is always equal to the price and cannot define a crossover.
    """
    _positive_integer(period, "SMA period")
    values = _prices(prices)
    if period > len(values):
        raise ValueError(f"SMA {period} needs at least {period} sessions; only {len(values)} available.")
    window: deque[float] = deque()
    total = 0.0
    result: list[Price] = []
    for price in values:
        if price is None:
            window.clear()
            total = 0.0
            result.append(None)
            continue
        window.append(price)
        total += price
        if len(window) > period:
            total -= window.popleft()
        result.append(total / period if len(window) == period else None)
    return result


@dataclass(frozen=True)
class Crossover:
    index: int  # zero based; the UI displays index + 1 as the session number
    price: float
    sma: float
    position: float | None = None  # Fractional session at the line-segment intersection.

    @property
    def plot_index(self):
        return self.index if self.position is None else self.position


def crossover_events(prices: Sequence[Price], sma: Sequence[Price]) -> tuple[Crossover, ...]:
    """Find upward events and estimate their piecewise-linear intersections.

    index retains the confirming EOD session for count/notification compatibility;
    price/sma and plot_index describe the estimated intersection of the two lines.
    """
    if len(prices) != len(sma):
        raise ValueError("Price and SMA series must have the same length.")
    events = []
    previous_side = None
    values, averages = _prices(prices), _prices(sma)
    for index, (price, average) in enumerate(zip(values, averages)):
        if price is None or average is None:
            previous_side = None
            continue
        side = 1 if price > average else -1 if price < average else 0
        if side == 0:
            continue
        if previous_side == -1 and side == 1:
            # The displayed daily series are joined by straight segments. Their
            # intersection estimates a crossing; it is not an observed intraday fill.
            before = values[index - 1] - averages[index - 1]
            after = price - average
            fraction = -before / (after - before)
            crossing_price = values[index - 1] + fraction * (price - values[index - 1])
            events.append(Crossover(index, crossing_price, crossing_price, index - 1 + fraction))
        previous_side = side
    return tuple(events)


def count_crossings(prices: Sequence[Price], sma: Sequence[Price]) -> int:
    return len(crossover_events(prices, sma))


@dataclass(frozen=True)
class OptimizationResult:
    period: int
    target_frequency: int
    history_sessions: int
    comparisons: int
    sma: tuple[Price, ...]
    events: tuple[Crossover, ...]

    @property
    def crossing_count(self) -> int:
        return len(self.events)

    @property
    def frequency(self):
        return annual_frequency(self.crossing_count, self.comparisons)

    @property
    def actual_annual_frequency(self) -> float:
        return float(self.frequency)

    @property
    def frequency_error(self):
        return abs(self.frequency - self.target_frequency)

    @property
    def usable_years(self) -> float:
        return self.comparisons / TRADING_SESSIONS_PER_YEAR

    @property
    def target_crossings(self) -> float:
        return self.target_frequency * self.usable_years


def optimize_sma(
    prices: Sequence[Price], target_frequency: int, candidates: Iterable[int] | None = None,
    *, cancel=None, use_fast=True,
) -> OptimizationResult:
    """Minimize annual-frequency error across all observable history.

    The automatic cap is min(floor(H/2),252) through H=756, then H-504.
    Each candidate must have at least H-cap actual observable comparisons,
    excluding warm-up, gaps, and re-warm-up. Explicit candidate lists are useful
    for tests but must obey the same cap and coverage rules as the app.
    Exact annual-rate ties choose the shorter SMA.
    """
    _positive_integer(target_frequency, "Target frequency")
    values = _prices(prices)
    if len(values) < 4:
        raise ValueError("At least 4 sessions are needed to optimize an SMA.")
    cap = maximum_sma_period(len(values))
    minimum = len(values) - cap
    periods = list(range(2, cap + 1)) if candidates is None else list(candidates)
    if not periods:
        raise ValueError("Choose at least one candidate SMA period.")
    for period in periods:
        _positive_integer(period, "Candidate period")
        if not 2 <= period <= cap:
            raise ValueError(f"Candidate periods must be between 2 and {cap} for this history.")
    if use_fast and len(values) > 1600:
        result = _fast_optimization(values, periods, minimum, target_frequency, cancel)
        if result is not None:
            return result
    best = None
    for period in sorted(set(periods)):
        if cancel is not None and cancel.is_set():
            raise ValueError("Optimization cancelled.")
        average = simple_moving_average(values, period)
        comparisons = observable_comparisons(values, average)
        if comparisons < minimum:
            continue
        result = OptimizationResult(period, target_frequency, len(values), comparisons,
                                    tuple(average), crossover_events(values, average))
        if best is None or (result.frequency_error, result.period) < (best.frequency_error, best.period):
            best = result
    if best is None:
        raise ValueError(f"Insufficient valid history: need at least {minimum} observable "
                         "price/SMA comparisons after warm-up and gaps.")
    return best


def _fast_optimization(values, periods, minimum, target, cancel):
    """Vectorized exhaustive scoring; exact reference output for the winner.

    Prefix arithmetic can differ from rolling arithmetic near equality. Such
    candidates use the reference engine, with a conservative accumulated-error
    bound. No candidate pruning, history truncation or approximate period grid.
    NumPy is optional (available with the desktop Yahoo dependency).
    """
    try:
        import numpy as np
    except ImportError:
        return None
    array = np.array([np.nan if x is None else x for x in values], dtype=float)
    finite = np.isfinite(array)
    clean = np.where(finite, array, 0)
    prefix = np.concatenate(([0.0], np.cumsum(clean)))
    missing = np.concatenate(([0], np.cumsum(~finite)))
    sum_abs = float(np.sum(np.abs(clean)))
    peak = float(np.max(np.abs(clean), initial=0)) + 1
    accumulated_error = 64 * np.finfo(float).eps * len(values)
    best_key, best_period = None, None
    for period in sorted(set(periods)):
        if cancel is not None and cancel.is_set():
            raise ValueError("Optimization cancelled.")
        average = np.full(len(values), np.nan)
        rolling = (prefix[period:] - prefix[:-period]) / period
        rolling[missing[period:] != missing[:-period]] = np.nan
        average[period-1:] = rolling
        valid = finite & np.isfinite(average)
        comparisons = int(np.count_nonzero(valid[1:] & valid[:-1]))
        if comparisons < minimum:
            continue
        delta = array - average
        bound = accumulated_error * (sum_abs / period + peak)
        if np.any(np.abs(delta[valid]) <= bound):
            exact = simple_moving_average(values, period)
            comparisons = observable_comparisons(values, exact)
            count = len(crossover_events(values, exact))
        else:
            tokens = np.where(valid, np.sign(delta), 0)[np.flatnonzero(~valid | (delta != 0))]
            count = int(np.count_nonzero((tokens[:-1] == -1) & (tokens[1:] == 1)))
        key = (abs(annual_frequency(count, comparisons) - target), period)
        if best_key is None or key < best_key:
            best_key, best_period = key, period
    if best_period is None:
        return None
    average = tuple(simple_moving_average(values, best_period))
    result = OptimizationResult(best_period, target, len(values),
                                observable_comparisons(values, average), average,
                                crossover_events(values, average))
    # Retain the reference route as a safety fallback for an unexpected numeric discrepancy.
    return result if (result.frequency_error, result.period) == best_key else None
