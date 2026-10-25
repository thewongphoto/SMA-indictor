"""Native Kivy canvas chart: no browser, Matplotlib, or platform-specific widget."""
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, Rectangle, Triangle
from kivy.metrics import dp, sp
from kivy.uix.widget import Widget

from .engine import crossover_events

PRICE_COLOR = (0.30, 0.87, 0.77, 1)
ACTIVE_COLOR = (1.0, 0.74, 0.36, 1)
SAVED_COLORS = ((0.59, 0.64, 1, 1), (1, 0.49, 0.62, 1), (0.42, 0.76, 1, 1))
MUTED = (0.58, 0.66, 0.75, 1)


class PriceChart(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prices = ()
        self.series = []
        self.marker_events = {}
        self.bind(pos=self.redraw, size=self.redraw)

    @staticmethod
    def line_color(line, index):
        return ACTIVE_COLOR if line.active else SAVED_COLORS[index % len(SAVED_COLORS)]

    def update(self, prices, series):
        # Keep exact engine output; never recalculate an approximation for plotting.
        self.prices = tuple(prices)
        self.series = list(series)
        self.marker_events = {line.key: crossover_events(self.prices, line.sma) for line in self.series}
        self.redraw()

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
            left, bottom = self.x + dp(38), self.y + dp(28)
            width, height = max(dp(1), self.width - dp(48)), max(dp(1), self.height - dp(44))
            values = [p for p in self.prices if p is not None]
            for line in self.series:
                values.extend(v for v in line.sma if v is not None)
            low, high = min(values), max(values)
            margin = max((high - low) * 0.13, 1)
            low, high = low - margin, high + margin

            def point(index, price):
                return (left + index / max(1, len(self.prices) - 1) * width,
                        bottom + (price - low) / (high - low) * height)

            for step in range(5):
                fraction = step / 4
                y = bottom + fraction * height
                Color(0.16, 0.21, 0.28, 1)
                Line(points=[left, y, left + width, y], width=dp(0.6))
                self._text(f"{low + fraction * (high - low):.0f}", self.x, y - dp(6))
            for index in [0, (len(self.prices) - 1) // 2, len(self.prices) - 1]:
                x, _ = point(index, low)
                self._text(str(index + 1), x, self.y + dp(8), center=True)

            def draw_series(values, color, thickness):
                points = []
                Color(*color)
                for index, value in enumerate(values):
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
                Color(*color)
                for event in self.marker_events[line.key]:
                    x, y = point(event.index, event.price)
                    r = dp(4)
                    Triangle(points=[x, y + r, x - r, y - r, x + r, y - r])
