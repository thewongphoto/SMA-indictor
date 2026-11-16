"""Testable presentation state shared by buttons, chart, cards, and event table."""
from dataclasses import dataclass
import hashlib
import json
import math

from .engine import OptimizationResult, Price, crossover_events, optimize_sma, simple_moving_average
from .market_data import PreviewMarketDataProvider
from .securities import security_by_key
from .policy import observable_comparisons,calendar_weights,observable_calendar_days
from .storage import LineStore, SavedLine
from .history_window import optimize_history, scoped_result, window_dates, label as history_label
from .line_names import sma_label


@dataclass(frozen=True)
class PlotLine:
    key: str
    period: int
    target_frequency: int
    sma: tuple[Price, ...]
    active: bool = False
    color_index: int | None = None
    name: str = ""
    history_start: str = ""
    history_end: str = ""


class AnalyzerModel:
    def __init__(self, store: LineStore, data_provider=None):
        self.store = store
        self.data_provider = data_provider or PreviewMarketDataProvider()
        self.dataset = (self.data_provider.initial_dataset() if hasattr(self.data_provider, "initial_dataset")
                        else self.data_provider.historical_data(security_by_key("DEMO-SGX"), "Oscillating"))
        self.history_start = self.history_end = ""
        self.editing_line_id = None
        self.target_frequency = 12
        self.result: OptimizationResult | None = None
        self.active_visible = True
        self.viewing_saved = False
        self.period_preserved = False
        self._fingerprint_cache = None

    def select_dataset(self, counter: str, scenario: str) -> None:
        # Generate before replacing state so invalid choices leave the current data intact.
        dataset = self.data_provider.historical_data(security_by_key(counter), scenario)
        self.apply_dataset(dataset)

    def security(self, key):
        """Persisted dynamic Yahoo identities and legacy preview identities coexist."""
        cache = getattr(self.data_provider, "cache", None)
        if cache:
            found = cache.security(key)
            if found:
                from .securities import register_security
                return register_security(found)
        return security_by_key(key)

    def library_lines(self):
        lines = self.store.list_all_lines()
        if not getattr(self.data_provider, "is_simulated", True):
            return [line for line in lines if line.counter.startswith("YAHOO:")]
        return lines

    def archive_lines(self):
        lines = self.store.recent_unsaved()
        if not getattr(self.data_provider, "is_simulated", True):
            return [line for line in lines if line.counter.startswith("YAHOO:")]
        return lines

    def apply_dataset(self, dataset):
        self.dataset = dataset
        self.history_start = self.history_end = ""
        self.editing_line_id = None
        self.result = None
        self.active_visible = True
        self.viewing_saved = False
        self.period_preserved = False
        self._fingerprint_cache = None

    def data_fingerprint(self):
        if self._fingerprint_cache is None or self._fingerprint_cache[0] is not self.dataset:
            data = self.dataset
            policy_version = 2 if getattr(data,"is_simulated",True) else 3
            payload = json.dumps((policy_version,self.history_start,self.history_end,data.version,getattr(data,"price_basis","example-close"),data.dates,
                [float(p) if p is not None and math.isfinite(p) else None for p in data.prices]),
                separators=(",",":"),allow_nan=False).encode()
            self._fingerprint_cache = (data,hashlib.sha256(payload).hexdigest())
        return self._fingerprint_cache[1]

    def remember_result(self,result):
        self.store.cache_choice(self.dataset.counter,self.dataset.scenario,result.target_frequency,
                                self.data_fingerprint(),result.period)

    def reuse_result(self):
        saved = [line for line in self.saved_lines() if line.target_frequency == self.target_frequency and (line.history_start,line.history_end)==(self.history_start,self.history_end)]
        for line in reversed(saved):
            try:
                result = self.result_for_dataset(self.dataset,line.period,line.target_frequency,line.history_start,line.history_end)
            except ValueError:
                continue
            self.apply_result(result)
            self.viewing_saved = True
            return True
        period = self.store.cached_choice(self.dataset.counter,self.dataset.scenario,
                                          self.target_frequency,self.data_fingerprint())
        if period is not None:
            self.apply_result(self.result_for_dataset(self.dataset,period,self.target_frequency,self.history_start,self.history_end))
            return True
        return False

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
            self.viewing_saved = False

    def calculate(self) -> OptimizationResult:
        """Synchronous route for tests and non-UI clients."""
        result = optimize_history(self.dataset.prices,self.target_frequency,dates=self.dataset.dates,
            history_start=self.history_start,history_end=self.history_end,
            simulated=getattr(self.dataset,'is_simulated',True))
        self.remember_result(result)
        self.apply_result(result)
        return result

    def apply_result(self, result: OptimizationResult) -> None:
        self.result = result
        self.active_visible = True
        self.viewing_saved = False
        self.period_preserved = False

    def view_saved_line(self, line_id: int) -> SavedLine:
        """Open exact saved parameters; never rerun or silently retune the optimizer.

        View reveals the selected overlay for this visit, even if it was hidden.
        Other lines' visibility and the saved settings themselves are unchanged.
        Validate before replacing the existing analysis so errors are recoverable.
        """
        prepared = self.prepare_saved_line(line_id)
        self.apply_saved_line(prepared)
        return prepared[0]

    @property
    def history_stale(self):
        return self.result is not None and (self.result.history_start,self.result.history_end)!=(self.history_start,self.history_end)

    def set_history(self,start='',end=''):
        from .history_window import validate
        start,end=window_dates(start,end)
        validate(self.dataset.prices,self.dataset.dates,start,end)
        current=self.current_saved_line()
        if current:self.editing_line_id=current.id
        self.history_start,self.history_end=start,end
        self._fingerprint_cache=None

    @staticmethod
    def result_for_dataset(data,period,target,history_start='',history_end=''):
        return scoped_result(data.prices,data.dates,period,target,history_start,history_end,
            simulated=getattr(data,'is_simulated',True))

    def prepare_saved_line(self, line_id):
        line = self.store.get_line(line_id)
        data = self.data_provider.historical_data(self.security(line.counter), line.scenario)
        result = self.result_for_dataset(data, line.period, line.target_frequency,line.history_start,line.history_end)
        return line, data, result

    def apply_saved_line(self, prepared):
        line, data, result = prepared
        self.dataset = data
        self.target_frequency = line.target_frequency
        self.history_start,self.history_end=line.history_start,line.history_end
        self._fingerprint_cache=None
        self.editing_line_id=line.id
        self.result = result
        self.active_visible = True
        self.viewing_saved = True
        self.period_preserved = False

    def saved_lines(self) -> list[SavedLine]:
        return self.store.list_lines(self.dataset.counter, self.dataset.scenario)

    def save_current(self,update=False) -> None:
        if self.result is None:
            raise ValueError("Press Optimize SMA before saving a line.")
        if self.history_stale:raise ValueError('Recalculate to match the selected price history before saving.')
        if update and self.editing_line_id:
            self.store.update_analysis(self.editing_line_id,self.result.period,self.result.target_frequency,self.result.history_start,self.result.history_end)
        else:
            as_new=self.editing_line_id is not None
            self.store.save(self.dataset.counter, self.dataset.scenario,
                        self.result.period, self.result.target_frequency,self.result.history_start,self.result.history_end)
            if as_new:
                line=self.current_saved_line()
                self.store.rename(line.id,'')
                self.store.set_notifications(line.id,'phone',True)
                for kind in ('buy','monitor','monitor_start'):self.store.set_line_alert(line.id,kind,True)
        self.editing_line_id=None

    def current_saved_line(self) -> SavedLine | None:
        if self.result is None:
            return None
        return next((line for line in self.saved_lines()
                     if (line.period, line.target_frequency,line.history_start,line.history_end) ==
                     (self.result.period, self.result.target_frequency,self.result.history_start,self.result.history_end)), None)

    def toggle_current_saved(self) -> bool:
        saved = self.current_saved_line()
        if saved is not None:
            self.store.delete(saved.id)
            if self.editing_line_id==saved.id:self.editing_line_id=None
            return False
        self.save_current()
        return True

    def plot_lines(self) -> list[PlotLine]:
        # Separate custom windows keep their own identities and colours.
        lines: dict[tuple, PlotLine] = {}
        for saved in self.saved_lines():
            if saved.visible and saved.period <= len(self.dataset.prices):
                lines[(saved.period,saved.history_start,saved.history_end)] = PlotLine(
                    f"saved-{saved.id}", saved.period, saved.target_frequency,
                    tuple(simple_moving_average(self.dataset.prices, saved.period)),
                    color_index=self.store.line_color_index(saved),
                    name=saved.display_name,history_start=saved.history_start,history_end=saved.history_end,
                )
        if self.result is not None:
            # Active visibility controls this period even if it was also saved.
            scope=(self.result.period,self.result.history_start,self.result.history_end)
            lines.pop(scope, None)
            if self.active_visible:
                lines[scope] = PlotLine(
                    "active", self.result.period, self.result.target_frequency, self.result.sma, True,
                    self.store.line_color_index(self.current_saved_line()) if self.current_saved_line() else self.store.color_index(self.dataset.counter,self.dataset.scenario,self.result.period),
                    self.current_line_name(), self.result.history_start,self.result.history_end,
                )
        return list(lines.values())

    def summary(self) -> dict[str, str]:
        if self.result is None:
            return {"period": "—", "target": f"{self.target_frequency} / yr", "actual": "—", "count": "—"}
        saved = self.current_saved_line()
        return {
            "period": saved.display_name if saved else self.current_line_name(),
            "target": f"{self.result.target_frequency} / yr",
            "actual": f"{self.result.actual_annual_frequency:.2f} / yr",
            "count": str(self.result.crossing_count),
        }

    def current_line_name(self):
        saved = self.current_saved_line()
        if saved:
            return saved.display_name
        if self.result is None:
            return "SMA"
        years = history_label(self.result.history_start, self.result.history_end, short=True)
        return sma_label(self.result.period) + (f" · {years}" if years else "")

    def event_rows(self) -> list[tuple[str, str, str]]:
        if self.result is None:
            return []
        live = not getattr(self.dataset, "is_simulated", True)
        return [(self.dataset.dates[event.index] if live else f"{event.index + 1:03d}",
                 f"{event.price:.4f}", f"{event.sma:.4f}")
                for event in self.result.events]
