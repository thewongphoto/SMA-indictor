"""Equal-budget, close-to-close historical illustrations; no trading prediction."""
from dataclasses import dataclass
import math
import random
from decimal import Decimal, InvalidOperation

from .settings import TRADING_SESSIONS_PER_YEAR


def period_sessions(label, custom_years, history_length):
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
    return min(history_length, sessions)


def valid_price(value):
    return value is not None and math.isfinite(value) and value > 0


@dataclass(frozen=True)
class InvestmentScenario:
    indices: tuple[int, ...]
    ending_value: float

    def difference_percent(self, reference):
        """Relative ending-value difference; zero reference has no defined ratio."""
        if reference.ending_value == 0:
            return None
        return (self.ending_value - reference.ending_value) / reference.ending_value * 100

    @property
    def invested(self):
        return len(self.indices) * 100.0


@dataclass(frozen=True)
class BacktestReport:
    start: int
    end: int
    eligible_sessions: int
    crossings: InvestmentScenario
    random: InvestmentScenario
    highest: InvestmentScenario
    positive_ranked_days: int


def compare_investments(prices, sma, events, sessions):
    """Invest $100 per selected close; hold fractional units to the final close.

    Use the same observable sessions for all three samples (including the
    crossing day's preceding close/SMA). Warm-up and gaps never manufacture
    opportunities. A fixed local seed makes the random comparison repeatable.
    Highest ranks daily close/previous close - 1, with earlier ties first.
    """
    if len(prices) != len(sma) or sessions < 1 or not prices:
        raise ValueError("A price/SMA history and a positive period are required.")
    end = len(prices) - 1
    if not valid_price(prices[end]):
        raise ValueError("The final EOD price is missing; ending values are unavailable.")
    start = max(0, len(prices) - sessions)
    eligible = [i for i in range(max(1, start), end + 1)
                if all(valid_price(v) for v in (prices[i-1], prices[i], sma[i-1], sma[i]))]
    eligible_set = set(eligible)
    crossings = sorted({event.index for event in events if event.index in eligible_set})
    count = len(crossings)
    random_indices = sorted(random.Random(73021).sample(eligible, count))
    ranked = sorted(eligible, key=lambda i: (-(prices[i] / prices[i-1] - 1), i))[:count]

    def investment(indices):
        return InvestmentScenario(tuple(indices), math.fsum(100 * prices[end] / prices[i] for i in indices))

    return BacktestReport(start, end, len(eligible), investment(crossings),
                          investment(random_indices), investment(ranked),
                          sum(prices[i] > prices[i-1] for i in ranked))
