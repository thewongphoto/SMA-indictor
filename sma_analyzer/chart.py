"""Native Kivy canvas chart: no browser, Matplotlib, or platform-specific widget."""
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from .engine import crossover_events
from .viewport import ChartViewport, RangeSelection

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
    to the chart even when it leaves the widget or visible scroll area.
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
        self.selection = None
        self._drag_touch = None
        self._anchor_x = 0
        self.bind(pos=self.redraw, size=self.redraw)

    @staticmethod
    def line_color(line, index):
        return ACTIVE_COLOR if line.active else SAVED_COLORS[index % len(SAVED_COLORS)]

    def update(self, prices, series):
        # Keep exact engine output; never recalculate an approximation for plotting.
        prices = tuple(prices)
        changed = prices != self.prices
        self.prices = prices
        self.series = list(series)
        self.marker_events = {line.key: crossover_events(self.prices, line.sma) for line in self.series}
        if changed:
            self._cancel_selection()
            self.viewport.reset(len(self.prices))
            self.viewport.show_timeline("1Y")
            self.timeline = "1Y"
            self._sync_view()
        self.redraw()

    def set_timeline(self, label):
        self._cancel_selection()
        self.viewport.show_timeline(label)
        self.timeline = label
        self._sync_view()
        self.redraw()

    @property
    def plot_rect(self):
        return (self.x + dp(38), self.y + dp(28),
                max(dp(1), self.width - dp(48)), max(dp(1), self.height - dp(44)))

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
        if self._drag_touch is not None:
            self._drag_touch.ungrab(self)
        self._drag_touch = None
        self.selection = None

    def on_touch_down(self, touch):
        if (self.disabled or len(self.prices) < 2
                or ('button' in touch.profile and touch.button != 'left')):
            return super().on_touch_down(touch)
        left, bottom, width, height = self.plot_rect
        if not (left <= touch.x <= left + width and bottom <= touch.y <= bottom + height):
            return super().on_touch_down(touch)
        # A second finger in the plot must not start scrolling during selection.
        if self._drag_touch is not None:
            return True
        if self.viewport.y_limits(self.prices) is None:
            return False
        self._drag_touch = touch
        self._anchor_x = touch.x
        anchor = self._index_at_x(touch.x)
        self.selection = RangeSelection(anchor, anchor)
        touch.grab(self)
        self.redraw()
        return True

    def on_touch_move(self, touch):
        if touch is self._drag_touch:
            if touch.grab_current is self:
                self.selection.cursor = self._index_at_x(touch.x)
                self.redraw()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch is self._drag_touch:
            if touch.grab_current is self:
                # Use the release position too: providers need not send a final move.
                final = self._index_at_x(touch.x)
                left, _, width, _ = self.plot_rect
                clamped_x = min(left + width, max(left, touch.x))
                if abs(clamped_x - self._anchor_x) >= dp(6):
                    self.viewport.select(self.selection.anchor, final)
                self._cancel_selection()
                self._sync_view()
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
                self._text(f"{value:.2f}" if high - low < 5 else f"{value:.0f}", self.x, y - dp(6))
            for index in sorted({start, (start + end) // 2, end}):
                x, _ = point(index, low)
                self._text(str(index + 1), x, self.y + dp(8), center=True)

            def draw_series(values, color, thickness):
                points = []
                Color(*color)
                for index in range(start, min(end + 1, len(values))):
                    value = values[index]
                    if value is None:
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
                    if not start <= event.index <= end:
                        continue
                    x, y = point(event.index, event.price)
                    draw_plus(x, y, dp(5), color)

            if self.selection is not None:
                x_start, _ = point(self.selection.start, low)
                x_end, _ = point(self.selection.end, low)
                Color(0.45, 0.73, 1, 0.18)
                Rectangle(pos=(x_start, bottom), size=(x_end - x_start, height))
                Color(*START_COLOR)
                Line(points=[x_start, bottom, x_start, bottom + height], width=dp(1.4))
                # At first contact show a single green anchor; left-to-right
                # ordering always assigns green to start and red to end.
                if x_end > x_start:
                    Color(*END_COLOR)
                    Line(points=[x_end, bottom, x_end, bottom + height], width=dp(1.4))
