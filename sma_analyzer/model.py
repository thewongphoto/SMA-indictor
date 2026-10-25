"""Testable presentation state shared by buttons, chart, cards, and event table."""
from dataclasses import dataclass

from .engine import OptimizationResult, Price, optimize_sma, simple_moving_average
from .mock_data import generate_mock_data
from .storage import LineStore, SavedLine


@dataclass(frozen=True)
class PlotLine:
    key: str
    period: int
    target_frequency: int
    sma: tuple[Price, ...]
    active: bool = False


class AnalyzerModel:
    def __init__(self, store: LineStore):
        self.store = store
        self.dataset = generate_mock_data("DEMO-SGX", "Oscillating")
        self.target_frequency = 12
        self.result: OptimizationResult | None = None
        self.active_visible = True

    def select_dataset(self, counter: str, scenario: str) -> None:
        # Generate before replacing state so invalid choices leave the current data intact.
        self.dataset = generate_mock_data(counter, scenario)
        self.result = None
        self.active_visible = True

    def set_target(self, text: str) -> None:
        try:
            value = int(text.strip())
        except (ValueError, AttributeError):
            raise ValueError("Enter a positive whole number of crossings per year, such as 12.") from None
        if value < 1:
            raise ValueError("Target frequency must be at least 1 crossing per year.")
        if value > 2**63 - 1:
            raise ValueError("Target frequency must fit a positive SQLite 64-bit whole number.")
        if value != self.target_frequency:
            self.target_frequency = value
            self.result = None
            self.active_visible = True

    def calculate(self) -> OptimizationResult:
        """Synchronous route for tests and non-UI clients."""
        result = optimize_sma(self.dataset.prices, self.target_frequency)
        self.apply_result(result)
        return result

    def apply_result(self, result: OptimizationResult) -> None:
        self.result = result
        self.active_visible = True

    def saved_lines(self) -> list[SavedLine]:
        return self.store.list_lines(self.dataset.counter, self.dataset.scenario)

    def save_current(self) -> None:
        if self.result is None:
            raise ValueError("Press Optimize SMA before saving a line.")
        self.store.save(self.dataset.counter, self.dataset.scenario,
                        self.result.period, self.result.target_frequency)

    def plot_lines(self) -> list[PlotLine]:
        # One visual line per period; the selected result has the primary color.
        lines: dict[int, PlotLine] = {}
        for saved in self.saved_lines():
            if saved.visible and saved.period <= len(self.dataset.prices):
                lines[saved.period] = PlotLine(
                    f"saved-{saved.id}", saved.period, saved.target_frequency,
                    tuple(simple_moving_average(self.dataset.prices, saved.period)),
                )
        if self.result is not None:
            # Active visibility controls this period even if it was also saved.
            lines.pop(self.result.period, None)
            if self.active_visible:
                lines[self.result.period] = PlotLine(
                    "active", self.result.period, self.result.target_frequency, self.result.sma, True,
                )
        return list(lines.values())

    def summary(self) -> dict[str, str]:
        if self.result is None:
            return {"period": "—", "target": f"{self.target_frequency} / yr", "actual": "—", "count": "—"}
        return {
            "period": f"{self.result.period} sessions",
            "target": f"{self.result.target_frequency} / yr",
            "actual": f"{self.result.actual_annual_frequency:.2f} / yr",
            "count": str(self.result.crossing_count),
        }

    def event_rows(self) -> list[tuple[str, str, str]]:
        if self.result is None:
            return []
        return [(f"{event.index + 1:03d}", f"{event.price:.4f}", f"{event.sma:.4f}")
                for event in self.result.events]
