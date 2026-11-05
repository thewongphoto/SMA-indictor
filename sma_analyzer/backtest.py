"""Equal-budget desktop illustrations using simulated crossing and EOD prices."""
from bisect import bisect_left
from dataclasses import dataclass
import math
import random
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from statistics import median
from datetime import date, timedelta

from .settings import TRADING_SESSIONS_PER_YEAR

RANDOM_SCENARIOS = 500


def period_sessions(label, custom_years, history_length, dates=None):
    if label == "Max":
        return history_length
    text = custom_years if label == "Custom" else label.removesuffix("Y")
    try:
        years = Decimal(text)
        if not years.is_finite() or years <= 0 or years > 100:
            raise ValueError
        sessions = int(years * TRADING_SESSIONS_PER_YEAR)
        if sessions < 2:
            raise ValueError
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Enter a positive number of years (up to 100, at least 2 sessions).") from None
    if dates:
        end = date.fromisoformat(dates[-1])
        whole = int(years)
        try:
            cutoff = end.replace(year=end.year-whole)
        except ValueError:
            cutoff = end.replace(year=end.year-whole, day=28)
        cutoff -= timedelta(days=float(years-whole) * 365.2425)
        return max(1, history_length-bisect_left(dates, cutoff.isoformat()))
    return min(history_length, sessions)


def valid_price(value):
    return value is not None and math.isfinite(value) and value > 0


@dataclass(frozen=True)
class InvestmentScenario:
    indices: tuple[int, ...]
    ending_value: float
    entry_prices: tuple[float, ...] = ()

    def difference_percent(self, reference):
        if reference.ending_value == 0:
            return None
        return (self.ending_value - reference.ending_value) / reference.ending_value * 100

    @property
    def invested(self):
        return len(self.indices) * 100.0

    @property
    def return_percent(self):
        return (self.ending_value/self.invested-1)*100 if self.invested else None

    @property
    def average_price(self):
        return math.fsum(self.entry_prices) / len(self.entry_prices) if self.entry_prices else None


@dataclass(frozen=True)
class RandomMode:
    seed: int
    rounded_price: int
    frequency: int


@dataclass(frozen=True)
class BacktestReport:
    start: int
    end: int
    eligible_sessions: int
    crossings: InvestmentScenario
    dca: InvestmentScenario
    random: InvestmentScenario
    random_average_prices: tuple[float, ...]
    random_mode: RandomMode | None
    outperformance_percent: float | None


def equal_period_indices(start, end, count, eligible, dates=None):
    """Buy at the start of each equal interval, including N=1.

    Equal periods use trading-session time, independently of SMA warm-up. If a
    scheduled close is missing, use the next valid close, preserving distinct
    dates and reserving enough remaining dates for the remaining purchases.
    """
    if not count:
        return ()
    length = end - start + 1
    targets = [start + j * length // count for j in range(count)]
    if dates:
        first = date.fromisoformat(dates[start])
        span = (date.fromisoformat(dates[end])-first).days + 1
        targets = [bisect_left(dates, (first + timedelta(days=j*span//count)).isoformat())
                   for j in range(count)]
    result, previous = [], -1
    for j, target in enumerate(targets):
        slot = max(previous + 1, min(bisect_left(eligible, target), len(eligible) - (count-j)))
        result.append(eligible[slot])
        previous = slot
    return tuple(result)


def modal_random_sample(averages):
    """Mode of whole-dollar arithmetic average prices (half dollars round up).

    Tied modes prefer the one nearest the overall median, then the lower dollar.
    The representative is an actual sample nearest that modal dollar, with seed
    order breaking ties. Its ending value uses its individual purchase prices,
    preserving $100 per buy rather than dividing the entire budget by a mean.
    """
    groups = {}
    for seed, value in enumerate(averages):
        dollar = int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        groups.setdefault(dollar, []).append(seed)
    center = median(averages)
    winner = min(groups, key=lambda dollar: (-len(groups[dollar]), abs(dollar-center), dollar))
    members = groups[winner]
    seed = min(members, key=lambda i: (abs(averages[i]-winner), i))
    return RandomMode(seed, winner, len(members))


def compare_investments(prices, sma, events, sessions, dates=None):
    """$100 per buy, held to final close; arithmetic prices define mode/rank.

    Scenario a buys at interpolated crossing prices, attributed to the confirming
    day's index. DCA and random samples use valid EOD closes across the entire
    selected period, including dates before the selected SMA finishes warming up.
    Seeds 0..499 each sample N distinct dates. Percentile counts strictly higher
    random arithmetic average prices, exactly as requested (not ending returns).
    """
    if len(prices) != len(sma) or sessions < 1 or not prices:
        raise ValueError("A price/SMA history and a positive period are required.")
    end = len(prices) - 1
    if not valid_price(prices[end]):
        raise ValueError("The final EOD price is missing; ending values are unavailable.")
    start = max(0, len(prices) - sessions)
    eligible = [i for i in range(start, end+1) if valid_price(prices[i])]
    eligible_set = set(eligible)
    selected = sorted((event for event in events if event.index in eligible_set and valid_price(event.price)),
                      key=lambda event: event.index)
    count = len(selected)
    if count > len(eligible) or len({event.index for event in selected}) != count:
            raise ValueError("Each session can have at most one upward crossing.")

    def investment(indices, entry_prices=None):
        entries = tuple(prices[i] for i in indices) if entry_prices is None else tuple(entry_prices)
        return InvestmentScenario(tuple(indices), math.fsum(100 * prices[end] / p for p in entries), entries)

    crossings = investment([event.index for event in selected], [event.price for event in selected])
    dca = investment(equal_period_indices(start, end, count, eligible, dates))
    if not count:
        return BacktestReport(start, end, len(eligible), crossings, dca, investment(()), (), None, None)
    samples = [investment(sorted(random.Random(seed).sample(eligible, count))) for seed in range(RANDOM_SCENARIOS)]
    averages = tuple(sample.average_price for sample in samples)
    mode = modal_random_sample(averages)
    outperform = 100 * sum(value > crossings.average_price for value in averages) / RANDOM_SCENARIOS
    return BacktestReport(start, end, len(eligible), crossings, dca, samples[mode.seed], averages, mode, outperform)
