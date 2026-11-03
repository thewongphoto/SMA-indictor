"""Isolated three-year lesson; uses the real optimizer and backtest engine."""
from dataclasses import dataclass
import math

from .backtest import compare_investments
from .engine import optimize_sma
from .mock_data import Dataset

INTRODUCTION = "New to moving averages and upward crossing buy signals?"
RECOVERY_HELP = (
    "An SMA smooths recent closing prices. An upward crossing occurs when price "
    "moves from below the SMA to above it. Some investors use it as a buy signal "
    "because it may suggest that the price is beginning to recover. Waiting for "
    "a crossing can filter out some buys while price is still below its average."
)
RISK_HELP = (
    "It does not guarantee a recovery or stop an investment falling after a buy. "
    "SMAs lag prices, and false crossings can be followed by renewed declines. "
    "This three-year simulated chart deliberately includes reversals as well as recoveries."
)
COMPARISON_HELP = (
    "Choose a crossing frequency to see its SMA and investment-return comparisons. "
    "The optimizer matches crossing frequency, not profit. The comparisons use "
    "$100 per buy: a. upward crossings; b. equal-period buys; c. the most common "
    "of 500 random-buy scenarios, with the same number of buys in each. "
    "These are simulations, not forecasts."
)


def lesson_dataset():
    return Dataset("DEMO-SGX", "Guided example", tuple(
        round(100 + .025*i + 12*math.sin(2*math.pi*i/100)
              + 3*math.sin(2*math.pi*i/19), 4) for i in range(3*252)))


@dataclass(frozen=True)
class Lesson:
    dataset: Dataset
    result: object
    report: object


def calculate_lesson(target):
    data = lesson_dataset()
    result = optimize_sma(data.prices, target)
    report = compare_investments(data.prices, result.sma, result.events, len(data.prices))
    return Lesson(data, result, report)
