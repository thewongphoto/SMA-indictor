"""Chart range math, independent of Kivy and the SMA optimization objective."""
from dataclasses import dataclass
import math
from .settings import TRADING_SESSIONS_PER_YEAR


def available_timelines(session_count):
    """1Y clamps to shorter histories; unavailable longer ranges are omitted."""
    return tuple(label for label, years in (("1Y", 1), ("3Y", 3), ("5Y", 5))
                 if years == 1 or session_count >= years * TRADING_SESSIONS_PER_YEAR) + ("Max",)


@dataclass
class RangeSelection:
    anchor: float
    cursor: float

    @property
    def start(self) -> float:
        return min(self.anchor, self.cursor)

    @property
    def end(self) -> float:
        return max(self.anchor, self.cursor)


class ChartViewport:
    """Inclusive global session indices; selecting again zooms within this range."""
    def __init__(self, session_count=0):
        self.reset(session_count)

    @property
    def bounds(self) -> tuple[int, int]:
        return self.start, self.end

    @property
    def is_zoomed(self) -> bool:
        return self.bounds != self.base_range

    def reset(self, session_count=None):
        if session_count is not None:
            self.session_count = session_count
            self.base_range = (0, max(0, self.session_count - 1))
        self.start, self.end = self.base_range

    def show_timeline(self, label):
        if label not in available_timelines(self.session_count):
            raise ValueError(f"{label} is not available for this price history.")
        sessions = self.session_count if label == "Max" else int(label[:-1]) * TRADING_SESSIONS_PER_YEAR
        self.base_range = (max(0, self.session_count - sessions), max(0, self.session_count - 1))
        self.reset()

    def index_at(self, fraction: float) -> float:
        """Map a plot-relative x position to the currently displayed history."""
        return self.start + min(1, max(0, fraction)) * (self.end - self.start)

    def select(self, first: float, last: float) -> bool:
        """Round outward to sessions; reject zero-width/empty selections.

        Outward rounding retains the observations bordering both endpoints.
        It guarantees at least two sessions for a nonzero drag. The widget also
        filters tiny movements in screen pixels before calling this method.
        """
        if self.session_count < 2 or first == last:
            return False
        low = max(self.start, min(self.end, min(first, last)))
        high = max(self.start, min(self.end, max(first, last)))
        start, end = math.floor(low), math.ceil(high)
        if start >= end or (start, end) == self.bounds:
            return False
        self.start, self.end = start, end
        return True

    def pinch(self, initial_bounds, anchor, fraction, scale):
        """Scale a two-finger gesture around its midpoint within the full history."""
        if self.session_count < 2 or not math.isfinite(scale) or scale <= 0:
            return False
        span = min(self.session_count - 1, max(1, (initial_bounds[1] - initial_bounds[0]) / scale))
        start = min(self.session_count - 1 - span, max(0, anchor - fraction * span))
        bounds = (round(start), round(start + span))
        if bounds[0] == bounds[1]:
            return False
        changed = bounds != self.bounds
        self.start, self.end = bounds
        return changed

    def y_limits(self, prices, averages=()) -> tuple[float, float] | None:
        """Scale only visible prices/overlays, ignoring gaps and adding padding."""
        values = [value for series in (prices, *averages)
                  for value in series[self.start:self.end + 1]
                  if value is not None and math.isfinite(value)]
        if not values:
            return None
        low, high = min(values), max(values)
        margin = max((high - low) * 0.13, 0.01)
        return low - margin, high + margin
