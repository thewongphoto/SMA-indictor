"""Native Kivy canvas chart: no browser, Matplotlib, or platform-specific widget."""
import math

from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, Rectangle, Ellipse, RoundedRectangle, PushMatrix, PopMatrix, Rotate
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from .engine import crossover_events
from .viewport import ChartViewport

PRICE_COLOR = (0.30, 0.87, 0.77, 1)
ACTIVE_COLOR = (1.0, 0.74, 0.36, 1)
SAVED_COLORS = ((0.59, 0.64, 1, 1), (1, 0.49, 0.62, 1), (0.42, 0.76, 1, 1))
MUTED = (0.58, 0.66, 0.75, 1)
START_COLOR = (0.22, 0.94, 0.43, 1)
END_COLOR = (1, 0.28, 0.32, 1)


def draw_plus(x, y, radius, color):
    """Shared chart/legend marker: filled plus with a thin black outer border."""
    r, arm = radius, radius * 0.3
    Color(*color)
    Rectangle(pos=(x - r, y - arm), size=(2 * r, 2 * arm))
    Rectangle(pos=(x - arm, y - r), size=(2 * arm, 2 * r))
    Color(0, 0, 0, 1)
    Line(points=[x-arm, y+r, x+arm, y+r, x+arm, y+arm, x+r, y+arm,
                 x+r, y-arm, x+arm, y-arm, x+arm, y-r, x-arm, y-r,
                 x-arm, y-arm, x-r, y-arm, x-r, y+arm, x-arm, y+arm],
         close=True, width=dp(0.45))


class ChartScrollView(ScrollView):
    """Let plot gestures start immediately instead of waiting for scroll_timeout.

    Everything outside the plot, including the mouse wheel, uses normal page
    scrolling. Kivy's touch grab delivers the selected pointer's moves/releases
    to the chart even when it leaves the widget or visible scroll area. One
    pointer inspects EOD values; two pointers switch to pinch zoom.
    """
    chart = None

    def on_touch_down(self, touch):
        if self.chart is not None and self.collide_point(*touch.pos) and not self.disabled:
            touch.push()
            try:
                touch.apply_transform_2d(self.chart.to_widget)
                accepted = self.chart.on_touch_down(touch)
            finally:
                touch.pop()
            if accepted:
                return True
        return super().on_touch_down(touch)


class PriceChart(Widget):
    is_zoomed = BooleanProperty(False)
    view_range = ListProperty([0, 0])
    timeline = StringProperty("1Y")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prices = ()
        self.series = []
        self.marker_events = {}
        self.viewport = ChartViewport()
        self.dates = ()
        self.inspection_sma = None
        self.inspection = None
        self._touches = []
        self._pinch = None
        self._pinch_finished = False
        self.bind(pos=self.redraw, size=self.redraw)

    @staticmethod
    def line_color(line, index):
        return PriceChart.period_color(line.period, line.active)

    @staticmethod
    def period_color(period, active=False):
        # Stable across hiding/showing other periods; shared with saved-row swatches.
        return ACTIVE_COLOR if active else SAVED_COLORS[(period - 2) % len(SAVED_COLORS)]

    def update(self, prices, series, dates=(), inspection_sma=None):
        # Keep exact engine output; never recalculate an approximation for plotting.
        prices = tuple(prices)
        changed = prices != self.prices
        self.prices = prices
        self.series = list(series)
        self.dates = tuple(dates)
        self.inspection_sma = inspection_sma
        self.marker_events = {line.key: crossover_events(self.prices, line.sma) for line in self.series}
        if changed:
            self._cancel_selection()
            self.viewport.reset(len(self.prices))
            self.viewport.show_timeline("1Y")
            self.timeline = "1Y"
            self._sync_view()
        if self.inspection is not None:
            left, _, width, _ = self.plot_rect
            start, end = self.viewport.bounds
            self._inspect(left + (self.inspection["index"]-start)/max(1, end-start)*width)
        self.redraw()

    def set_timeline(self, label):
        self._cancel_selection()
        self.viewport.show_timeline(label)
        self.timeline = label
        self._sync_view()
        self.redraw()

    @property
    def plot_rect(self):
        return (self.x + dp(48), self.y + dp(40),
                max(dp(1), self.width - dp(62)), max(dp(1), self.height - dp(56)))

    def _index_at_x(self, x):
        left, _, width, _ = self.plot_rect
        return self.viewport.index_at((x - left) / width)

    def _sync_view(self):
        self.is_zoomed = self.viewport.is_zoomed
        self.view_range = list(self.viewport.bounds)

    def reset_zoom(self, *_):
        self._cancel_selection()
        self.viewport.reset()
        self._sync_view()
        self.redraw()

    def _cancel_selection(self):
        for touch in self._touches:
            touch.ungrab(self)
        self._touches = []
        self._pinch = None
        self._pinch_finished = False
        self.inspection = None

    def _inspect(self, x):
        start, end = self.viewport.bounds
        index = round(self._index_at_x(x))
        valid = [i for i in range(start, end + 1)
                 if self.prices[i] is not None and math.isfinite(self.prices[i])]
        if not valid:
            self.inspection = None
            return
        index = min(valid, key=lambda i: (abs(i - index), i))
        period, average = self.inspection_sma or (None, ())
        self.inspection = {"index": index, "date": self.dates[index] if self.dates else f"Session {index+1}",
                           "price": self.prices[index], "period": period,
                           "sma": average[index] if index < len(average) else None}

    def on_touch_down(self, touch):
        if (self.disabled or len(self.prices) < 2
                or ('button' in touch.profile and touch.button != 'left')):
            return super().on_touch_down(touch)
        left, bottom, width, height = self.plot_rect
        if not (left <= touch.x <= left + width and bottom <= touch.y <= bottom + height):
            return super().on_touch_down(touch)
        if touch in self._touches or len(self._touches) >= 2:
            return True
        if self.viewport.y_limits(self.prices) is None:
            return False
        self._touches.append(touch)
        touch.grab(self)
        if len(self._touches) == 1:
            self._pinch_finished = False
            self._inspect(touch.x)
        else:
            first, second = self._touches
            midpoint = (first.x + second.x) / 2
            distance = math.hypot(first.x - second.x, first.y - second.y)
            self._pinch = (self.viewport.bounds, self._index_at_x(midpoint), max(dp(6), distance))
            self.inspection = None
        self.redraw()
        return True

    def on_touch_move(self, touch):
        if touch in self._touches:
            if touch.grab_current is self:
                if len(self._touches) == 2 and self._pinch is not None:
                    first, second = self._touches
                    bounds, anchor, initial_distance = self._pinch
                    distance = max(dp(1), math.hypot(first.x-second.x, first.y-second.y))
                    left, _, width, _ = self.plot_rect
                    fraction = min(1, max(0, ((first.x+second.x)/2-left)/width))
                    self.viewport.pinch(bounds, anchor, fraction, distance/initial_distance)
                    self._sync_view()
                elif not self._pinch_finished:
                    self._inspect(touch.x)
                self.redraw()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch in self._touches:
            if touch.grab_current is self:
                if self._pinch is not None:
                    self._pinch_finished = True
                    self._pinch = None
                elif not self._pinch_finished:
                    self._inspect(touch.x)
                touch.ungrab(self)
                self._touches.remove(touch)
                self.redraw()
            return True
        return super().on_touch_up(touch)

    def _text(self, text, x, y, color=MUTED, center=False):
        label = CoreLabel(text=text, font_size=sp(10), color=color)
        label.refresh()
        width, height = label.texture.size
        Color(1, 1, 1, 1)
        Rectangle(texture=label.texture, pos=(x - width / 2 if center else x, y), size=(width, height))

    def redraw(self, *_):
        self.canvas.clear()
        with self.canvas:
            if not self.prices or not any(p is not None for p in self.prices):
                self._text("No simulated prices. Choose a scenario to begin.",
                           self.center_x, self.center_y, center=True)
                return
            left, bottom, width, height = self.plot_rect
            limits = self.viewport.y_limits(self.prices, [line.sma for line in self.series])
            if limits is None:
                self._text("No valid prices in this range. Use Zoom out.",
                           self.center_x, self.center_y, center=True)
                return
            low, high = limits
            start, end = self.viewport.bounds

            def point(index, price):
                return (left + (index - start) / max(1, end - start) * width,
                        bottom + (price - low) / (high - low) * height)

            for step in range(5):
                fraction = step / 4
                y = bottom + fraction * height
                Color(0.16, 0.21, 0.28, 1)
                Line(points=[left, y, left + width, y], width=dp(0.6))
                value = low + fraction * (high - low)
                self._text(f"{value:.2f}" if high - low < 5 else f"{value:.0f}", self.x + dp(12), y - dp(6))
            ticks = 6 if width >= dp(550) else 3
            for index in sorted({round(start + (end - start) * n / (ticks - 1)) for n in range(ticks)}):
                x, _ = point(index, low)
                Color(0.13, 0.18, 0.24, 1)
                Line(points=[x, bottom, x, bottom + height], width=dp(0.5))
                self._text(str(index + 1), x, self.y + dp(20), center=True)
            Color(*MUTED)
            Line(points=[left, bottom + height, left, bottom, left + width, bottom], width=dp(0.6))
            self._text("Session", left + width / 2, self.y, center=True)
            PushMatrix()
            Rotate(angle=90, origin=(self.x + dp(3), bottom + height / 2))
            self._text("Price", self.x + dp(3), bottom + height / 2, center=True)
            PopMatrix()

            def draw_series(values, color, thickness):
                points = []
                Color(*color)
                for index in range(start, min(end + 1, len(values))):
                    value = values[index]
                    if value is None or not math.isfinite(value):
                        if len(points) >= 4:
                            Line(points=points, width=thickness)
                        points = []
                    else:
                        points.extend(point(index, value))
                if len(points) >= 4:
                    Line(points=points, width=thickness)

            draw_series(self.prices, PRICE_COLOR, dp(1.2))
            for index, line in enumerate(self.series):
                color = self.line_color(line, index)
                draw_series(line.sma, color, dp(1.6) if line.active else dp(1))
                for event in self.marker_events[line.key]:
                    if not start <= event.plot_index <= end:
                        continue
                    x, y = point(event.plot_index, event.price)
                    draw_plus(x, y, dp(5), color)

            if self.inspection is not None:
                info = self.inspection
                index = info["index"]
                if start <= index <= end:
                    x, y = point(index, info["price"])
                    Color(*MUTED)
                    Line(points=[x, bottom, x, bottom + height], width=dp(1))
                    Color(*PRICE_COLOR)
                    Ellipse(pos=(x-dp(3), y-dp(3)), size=(dp(6), dp(6)))
                    sma = "Unavailable (warm-up/gap)" if info["sma"] is None else f'{info["sma"]:.4f}'
                    caption = f'Simulated date: {info["date"]}\nEOD: {info["price"]:.4f}\n'
                    caption += f'SMA {info["period"]}: {sma}' if info["period"] else 'SMA: optimize first'
                    label = CoreLabel(text=caption, font_size=sp(10), color=(0.94, 0.97, 1, 1),
                                      text_size=(min(dp(205), self.width-dp(20)), None))
                    label.refresh()
                    w, h = label.texture.size
                    box_w, box_h = w+dp(12), h+dp(12)
                    box_x = x+dp(9) if x+dp(9)+box_w <= self.right else x-box_w-dp(9)
                    box_x = max(self.x+dp(2), min(self.right-box_w-dp(2), box_x))
                    box_y = max(bottom, min(bottom+height-box_h, y+dp(8)))
                    Color(0.08, 0.13, 0.20, 0.97)
                    RoundedRectangle(pos=(box_x, box_y), size=(box_w, box_h), radius=[dp(5)])
                    Color(1, 1, 1, 1)
                    Rectangle(texture=label.texture, pos=(box_x+dp(6), box_y+dp(6)), size=(w, h))
