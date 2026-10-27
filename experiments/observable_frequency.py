"""Proposed frequency scoring and history cap, isolated from the running app.

This module reuses the current SMA arithmetic and crossing events unchanged.
It measures exposure in adjacent valid price/SMA observations. For complete
history of length H and period N, that exposure is H-N comparisons: the first
SMA establishes a baseline, and the following observation can cross it.
"""
from dataclasses import dataclass
from fractions import Fraction
import math
from numbers import Real

from sma_analyzer.engine import Crossover, Price, crossover_events, simple_moving_average
from sma_analyzer.settings import TRADING_SESSIONS_PER_YEAR as YEAR


def _integer(value, name, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be a whole number of at least {minimum}.")


def proposed_cap(history_sessions: int) -> int:
    """The agreed continuous cap; this is not used by the application yet."""
    _integer(history_sessions, "History length")
    if history_sessions <= 3 * YEAR:
        return min(history_sessions // 2, YEAR)
    return history_sessions - 2 * YEAR


def observable_comparisons(prices, sma) -> int:
    """Count adjacent, finite price/SMA pairs, including equal-to-SMA pairs.

    A missing observation or SMA breaks exposure. The first valid observation
    after a gap establishes a fresh baseline, matching the engine's event rules.
    Missing sessions and the SMA re-warm-up are never included as exposure.
    """
    if len(prices) != len(sma):
        raise ValueError("Price and SMA series must have the same length.")

    def valid(value):
        if value is None:
            return False
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError("Prices and SMA values must be numbers or None.")
        return math.isfinite(value)

    previous_valid = False
    count = 0
    for price, average in zip(prices, sma):
        price_valid, average_valid = valid(price), valid(average)
        current_valid = price_valid and average_valid
        count += int(previous_valid and current_valid)
        previous_valid = current_valid
    return count


def annual_frequency(crossings: int, comparisons: int) -> Fraction:
    """Exact rate for reliable equal-error tie-breaking; UI may format as float."""
    _integer(crossings, "Crossing count", minimum=0)
    _integer(comparisons, "Observable comparisons")
    if crossings > comparisons:
        raise ValueError("Crossings cannot exceed observable comparisons.")
    return Fraction(crossings * YEAR, comparisons)


@dataclass(frozen=True)
class CandidateEvaluation:
    period: int
    target_frequency: int
    history_sessions: int
    comparisons: int
    sma: tuple[Price, ...]
    events: tuple[Crossover, ...]

    @property
    def crossing_count(self):
        return len(self.events)

    @property
    def frequency(self) -> Fraction:
        return annual_frequency(self.crossing_count, self.comparisons)

    @property
    def frequency_error(self) -> Fraction:
        return abs(self.frequency - self.target_frequency)


def evaluate_candidate(prices, period: int, target: int) -> CandidateEvaluation:
    _integer(target, "Target frequency")
    average = simple_moving_average(prices, period)
    comparisons = observable_comparisons(prices, average)
    if comparisons == 0:
        raise ValueError("No observable price/SMA comparisons for this candidate.")
    return CandidateEvaluation(period, target, len(prices), comparisons,
                               tuple(average), crossover_events(prices, average))


def best_candidate(prices, target, candidates, minimum_comparisons=1):
    """Research helper for comparing scoring alone with the complete proposal.

    The explicit candidate list permits controlled tests of the scoring change.
    The proposed policy below has no user-configurable cap or coverage override.
    """
    _integer(target, "Target frequency")
    _integer(minimum_comparisons, "Minimum observable comparisons")
    periods = list(candidates)
    if not periods:
        raise ValueError("No candidate periods are available.")
    for period in periods:
        _integer(period, "Candidate period", minimum=2)
        if period >= len(prices):
            raise ValueError("Candidates need at least one observation after the first SMA.")
    best = None
    for period in sorted(set(periods)):
        average = simple_moving_average(prices, period)
        comparisons = observable_comparisons(prices, average)
        if comparisons < minimum_comparisons:
            continue
        result = CandidateEvaluation(period, target, len(prices), comparisons,
                                     tuple(average), crossover_events(prices, average))
        if best is None or (result.frequency_error, result.period) < (best.frequency_error, best.period):
            best = result
    if best is None:
        raise ValueError(f"Insufficient valid history: need at least {minimum_comparisons} "
                         "observable price/SMA comparisons after warm-up and gaps.")
    return best


def optimize_proposed(prices, target) -> CandidateEvaluation:
    """Test the proposed cap/rate together without changing the app optimizer.

    Missing data can invalidate the duration promised by a cap based on raw
    history length. Require the actual exposure to reach H-cap as well: at least
    504 comparisons for histories over three years, and the corresponding
    shorter-history minimum otherwise. Report insufficient history if it cannot.
    """
    if len(prices) < 4:
        raise ValueError("At least 4 sessions are needed for the proposed policy.")
    cap = proposed_cap(len(prices))
    return best_candidate(prices, target, range(2, cap + 1), len(prices) - cap)
