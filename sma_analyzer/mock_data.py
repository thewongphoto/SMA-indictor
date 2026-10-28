"""Reproducible fictional series, never downloaded or described as market history."""
from dataclasses import dataclass
import math
import random

from .settings import COUNTERS, DATA_VERSION, SCENARIOS, MOCK_HISTORY_SESSIONS


@dataclass(frozen=True)
class Dataset:
    counter: str
    scenario: str
    prices: tuple[float, ...]
    version: int = DATA_VERSION

    @property
    def label(self) -> str:
        return f"{self.counter} · {self.scenario} · SIMULATED DATA"


def generate_mock_data(counter: str, scenario: str, sessions: int = MOCK_HISTORY_SESSIONS) -> Dataset:
    if counter not in COUNTERS or scenario not in SCENARIOS:
        raise ValueError("Choose a fictional counter and one of the three mock scenarios.")
    if isinstance(sessions, bool) or not isinstance(sessions, int) or sessions < 1:
        raise ValueError("The number of simulated sessions must be a positive integer.")
    # Explicit integer IDs avoid Python's process-randomized hash().
    rng = random.Random(73021 + 1000 * COUNTERS.index(counter) + 100 * SCENARIOS.index(scenario))
    offset = 40.0 * COUNTERS.index(counter)
    values = []
    noise = 0.0
    for t in range(sessions):
        if scenario == "Trending":
            price = 70 + offset + 0.22 * t + 1.4 * math.sin(t / 22) + rng.gauss(0, 0.7)
        elif scenario == "Oscillating":
            price = 100 + offset + 8 * math.sin(2 * math.pi * t / 20) + 3 * math.sin(t / 7) + rng.gauss(0, 0.4)
        else:
            noise = 0.75 * noise + rng.gauss(0, 0.75)
            price = 100 + offset + noise
        values.append(round(max(1.0, price), 4))
    return Dataset(counter, scenario, tuple(values))
