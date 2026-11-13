"""Compare real observations inside the plot, without fetching or interpolating."""
from dataclasses import dataclass
from datetime import date
import math


@dataclass(frozen=True)
class VisiblePriceChange:
    first: int
    last: int
    change: float
    percent: float | None

    @property
    def direction(self):
        return "up" if self.change > 0 else "down" if self.change < 0 else "flat"


def visible_price_change(prices, bounds):
    """Use the first/last finite closes actually inside fractional zoom bounds."""
    if not prices or not all(math.isfinite(value) for value in bounds):
        return None
    first, last = max(0, math.ceil(bounds[0])), min(len(prices)-1, math.floor(bounds[1]))
    def valid(index):
        return prices[index] is not None and math.isfinite(prices[index])
    while first <= last and not valid(first):
        first += 1
    while last >= first and not valid(last):
        last -= 1
    if first > last:
        return None
    change = prices[last] - prices[first]
    percent = change / prices[first] * 100 if prices[first] else None
    return VisiblePriceChange(first, last, change, percent)


def comparison_period(change, dates, timeline, zoomed):
    if not zoomed:
        return f"PAST {timeline.upper()}"
    if change is None or len(dates) <= change.last:
        return "VISIBLE RANGE"
    def formatted(index):
        # English month names remain stable across device locales.
        day = date.fromisoformat(dates[index])
        month = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[day.month-1]
        return f"{day.day:02d} {month} '{day.year % 100:02d}"
    return f"{formatted(change.first)} - {formatted(change.last)}"


def currency_prefix(currency):
    # The owner asked for a plain $ for every listing (US and SGX). Charts still
    # name the quote currency in their caption, e.g. "SGD adjusted daily close".
    # Data without a quote currency (legacy demo data) still gets no symbol.
    return "$" if currency else ""
