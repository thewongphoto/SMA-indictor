"""Chart range math, independent of Kivy and the SMA optimization objective."""
from dataclasses import dataclass
import math


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
        return self.bounds != (0, max(0, self.session_count - 1))

    def reset(self, session_count=None):
        if session_count is not None:
            self.session_count = session_count
        self.start, self.end = 0, max(0, self.session_count - 1)

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
