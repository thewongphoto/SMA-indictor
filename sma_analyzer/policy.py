"""Usable-history frequency and coverage policy shared by the application."""
from fractions import Fraction
import math
from numbers import Real

from .settings import TRADING_SESSIONS_PER_YEAR as YEAR


def _integer(value, name, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be a whole number of at least {minimum}.")


def maximum_sma_period(history_sessions: int) -> int:
    """Automatic history-dependent cap; not a user-configurable setting."""
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
