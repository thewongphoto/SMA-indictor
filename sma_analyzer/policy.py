"""Usable-history frequency and coverage policy shared by the application."""
from fractions import Fraction
import math
from numbers import Real
from datetime import date

from .settings import TRADING_SESSIONS_PER_YEAR as YEAR

CALENDAR_DAYS_PER_YEAR = 365


def calendar_weights(dates, history_length):
    """Elapsed days between real closes, including weekends and holidays."""
    if dates is None:
        return None  # Legacy date-free experiments/synthetic fixtures only.
    if len(dates) != history_length:
        raise ValueError("Every closing price needs its actual session date.")
    try:
        ordinals = tuple(date.fromisoformat(value).toordinal() for value in dates)
    except (ValueError, TypeError):
        raise ValueError("Session dates must be valid ISO calendar dates.") from None
    differences = tuple(right-left for left,right in zip(ordinals,ordinals[1:]))
    if any(days <= 0 for days in differences):
        raise ValueError("Session dates must be strictly increasing and unique.")
    return (0, *differences) if ordinals else ()


def observable_calendar_days(prices, sma, weights):
    """Calendar exposure over observable adjacent pairs; exclude warm-up/gaps."""
    if weights is None:
        return None
    if len(prices) != len(sma) or len(prices) != len(weights):
        raise ValueError("Prices, SMA and elapsed-day weights must have equal lengths.")
    previous_valid, elapsed = False, 0
    for index,(price,average) in enumerate(zip(prices,sma)):
        valid = (price is not None and average is not None and
                 math.isfinite(price) and math.isfinite(average))
        if previous_valid and valid:
            elapsed += weights[index]
        previous_valid = valid
    return elapsed


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


def annual_frequency(crossings: int, comparisons: int, calendar_days=None) -> Fraction:
    """Exact rate for reliable equal-error tie-breaking; UI may format as float."""
    _integer(crossings, "Crossing count", minimum=0)
    _integer(comparisons, "Observable comparisons")
    if crossings > comparisons:
        raise ValueError("Crossings cannot exceed observable comparisons.")
    if calendar_days is not None:
        _integer(calendar_days, "Observable calendar days")
        return Fraction(crossings * CALENDAR_DAYS_PER_YEAR, calendar_days)
    return Fraction(crossings * YEAR, comparisons)
