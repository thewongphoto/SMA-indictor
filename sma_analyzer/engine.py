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


def crossover_events(prices: Sequence[Price], sma: Sequence[Price]) -> tuple[Crossover, ...]:
    """Find upward crossings using strict numeric comparisons and the rules above."""
    if len(prices) != len(sma):
        raise ValueError("Price and SMA series must have the same length.")
    events = []
    previous_side = None
    for index, (price, average) in enumerate(zip(_prices(prices), _prices(sma))):
        if price is None or average is None:
            previous_side = None
            continue
        side = 1 if price > average else -1 if price < average else 0
        if side == 0:
            continue
        if previous_side == -1 and side == 1:
            events.append(Crossover(index, price, average))
        previous_side = side
    return tuple(events)


def count_crossings(prices: Sequence[Price], sma: Sequence[Price]) -> int:
    return len(crossover_events(prices, sma))


@dataclass(frozen=True)
class OptimizationResult:
    period: int
    target_frequency: int
    history_sessions: int
    target_crossings: float
    sma: tuple[Price, ...]
    events: tuple[Crossover, ...]

    @property
    def crossing_count(self) -> int:
        return len(self.events)

    @property
    def actual_annual_frequency(self) -> float:
        return self.crossing_count * TRADING_SESSIONS_PER_YEAR / self.history_sessions

    @property
    def count_error(self) -> float:
        return abs(self.crossing_count - self.target_crossings)


def optimize_sma(
    prices: Sequence[Price], target_frequency: int, candidates: Iterable[int] | None = None,
) -> OptimizationResult:
    """Search the entire history; minimize count error, then choose shorter N.

    The default candidate set is 2..len(history)-1, inclusive. Each candidate
    uses all its valid observations after its own warm-up (no common trimmed
    window). The target is frequency * len(history) / 252, including warm-up
    and missing sessions in the denominator. This follows the requested whole-
    history frequency, and can favor long periods with little usable history.
    Candidates require at least two adjacent valid price/SMA observations.
    """
    _positive_integer(target_frequency, "Target frequency")
    values = _prices(prices)
    if len(values) < 3:
        raise ValueError("At least 3 sessions are needed to optimize an SMA.")
    periods = list(range(2, len(values))) if candidates is None else list(candidates)
    if not periods:
        raise ValueError("Choose at least one candidate SMA period.")
    for period in periods:
        _positive_integer(period, "Candidate period")
        if not 2 <= period < len(values):
            raise ValueError(f"Candidate periods must be between 2 and {len(values) - 1}.")
    target = target_frequency * len(values) / TRADING_SESSIONS_PER_YEAR
    results = []
    for period in sorted(set(periods)):
        average = simple_moving_average(values, period)
        if not any(a is not None and b is not None for a, b in zip(average, average[1:])):
            continue
        results.append(OptimizationResult(
            period, target_frequency, len(values), target, tuple(average),
            crossover_events(values, average),
        ))
    if not results:
        raise ValueError("Not enough consecutive valid prices. Provide at least 3 without gaps.")
    return min(results, key=lambda result: (result.count_error, result.period))
