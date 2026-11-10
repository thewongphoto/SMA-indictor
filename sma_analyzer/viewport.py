"""Chart range math, independent of Kivy and the SMA optimization objective."""
from dataclasses import dataclass
import math
from datetime import date,timedelta
from calendar import monthrange
from bisect import bisect_left
from .settings import TRADING_SESSIONS_PER_YEAR
from .policy import CALENDAR_DAYS_PER_YEAR


SHORT_TIMELINES = ("3M", "6M", "9M", "1Y")


def months_before(day, months):
    """Subtract calendar months, clamping dates such as May 31 to February 28."""
    year, month = divmod(day.year * 12 + day.month - 1 - months, 12)
    month += 1
    return day.replace(year=year, month=month, day=min(day.day, monthrange(year, month)[1]))


def available_timelines(session_count, dates=()):
    """Short presets clamp to available data; incomplete 3Y/5Y ranges are omitted."""
    if dates:
        last = date.fromisoformat(dates[-1])
        def covered(years):
            cutoff = last - timedelta(days=years * CALENDAR_DAYS_PER_YEAR)
            return dates[0] <= cutoff.isoformat()
        return SHORT_TIMELINES + tuple(label for label, years in (("3Y",3),("5Y",5))
                     if covered(years)) + ("Max",)
    return SHORT_TIMELINES + tuple(label for label, years in (("3Y", 3), ("5Y", 5))
                 if session_count >= years * TRADING_SESSIONS_PER_YEAR) + ("Max",)


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
        self.dates = ()
        self.reset(session_count)

    @property
    def bounds(self) -> tuple[float, float]:
        return self.start, self.end

    @property
    def is_zoomed(self) -> bool:
        return any(not math.isclose(a,b,abs_tol=1e-8) for a,b in zip(self.bounds,self.base_range))

    def reset(self, session_count=None):
        if session_count is not None:
            self.session_count = session_count
            self.base_range = (0, max(0, self.session_count - 1))
        self.start, self.end = self.base_range

    def show_timeline(self, label):
        if label not in available_timelines(self.session_count, self.dates):
            raise ValueError(f"{label} is not available for this price history.")
        months = 0 if label == "Max" else int(label[:-1]) * (12 if label.endswith("Y") else 1)
        sessions = self.session_count if label == "Max" else months * TRADING_SESSIONS_PER_YEAR // 12
        self.base_range = (max(0, self.session_count - sessions), max(0, self.session_count - 1))
        if self.dates and label != "Max":
            last = date.fromisoformat(self.dates[-1])
            cutoff = (last - timedelta(days=int(label[:-1]) * CALENDAR_DAYS_PER_YEAR)
                      if label.endswith("Y") else months_before(last, months))
            self.base_range = (bisect_left(self.dates, cutoff.isoformat()), self.session_count-1)
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
        bounds = (start, start + span)
        if bounds[0] == bounds[1]:
            return False
        changed = any(not math.isclose(a,b,abs_tol=1e-8) for a,b in zip(bounds,self.bounds))
        self.start, self.end = bounds
        return changed

    def y_limits(self, prices, averages=()) -> tuple[float, float] | None:
        """Scale only visible prices/overlays, ignoring gaps and adding padding."""
        first,last = max(0,math.floor(self.start)),min(self.session_count,math.ceil(self.end)+1)
        values = [value for series in (prices, *averages)
                  for value in series[first:last]
                  if value is not None and math.isfinite(value)]
        if not values:
            return None
        low, high = min(values), max(values)
        margin = max((high - low) * 0.13, 0.01)
        return low - margin, high + margin
