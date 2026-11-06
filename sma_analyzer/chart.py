"""Native Kivy canvas chart: no browser, Matplotlib, or platform-specific widget."""
import math
from collections import OrderedDict
from kivy.clock import Clock

from kivy.core.text import Label as CoreLabel
from kivy.graphics import (Color, Line, Rectangle, Ellipse, RoundedRectangle, PushMatrix,
                          PopMatrix, Rotate, StencilPush, StencilUse, StencilUnUse, StencilPop)
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from .engine import crossover_events
from .viewport import ChartViewport
from .axis import date_ticks
from .line_names import sma_label
from .palette import line_color as palette_color

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
    price_label = StringProperty("EOD")
    inspection_name = StringProperty("")

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
        self._positions = {}
        self._pinch_clock = None
        self._display_limits = None
        self._smooth_limits = False
        self._textures = OrderedDict()
        self.axis_ticks = ()
        self._redraw_trigger = Clock.create_trigger(self.redraw,0)
        self.bind(pos=self.redraw, size=self.redraw)

    @staticmethod
    def line_color(line, index):
        if line.color_index is not None:
            return palette_color(line.color_index)
        return PriceChart.period_color(line.period, line.active)

    @staticmethod
    def period_color(period, active=False):
        # Stable across hiding/showing other periods; shared with saved-row swatches.
        return ACTIVE_COLOR if active else SAVED_COLORS[(period - 2) % len(SAVED_COLORS)]

    def update(self, prices, series, dates=(), inspection_sma=None, calendar_dates=False, price_label="EOD",inspection_name=""):
        # Keep exact engine output; never recalculate an approximation for plotting.
        prices = tuple(prices)
        changed = prices != self.prices or tuple(dates) != self.dates
        self.prices = prices
        self.series = list(series)
        self.dates = tuple(dates)
        self.viewport.dates = self.dates if calendar_dates else ()
        self.inspection_sma = inspection_sma
        self.price_label = price_label
        self.inspection_name = inspection_name
        self.marker_events = {line.key: crossover_events(self.prices, line.sma) for line in self.series}
        if changed:
            self._cancel_selection()
            self._display_limits = None
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
        self._display_limits = None
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
        self._display_limits = None
        self._sync_view()
        self.redraw()

    def _cancel_selection(self):
        for touch in self._touches:
            touch.ungrab(self)
        self._touches = []
        self._positions.clear()
        self._pinch = None
        self._pinch_finished = False
        self.inspection = None
        if self._pinch_clock is not None:
            self._pinch_clock.cancel()
            self._pinch_clock = None
        self._redraw_trigger.cancel()
        self._smooth_limits = False

    def _inspect(self, x):
        start, end = self.viewport.bounds
        index = round(self._index_at_x(x))
        valid = [i for i in range(max(0,math.ceil(start)), min(len(self.prices),math.floor(end)+1))
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
        self._positions[touch.uid] = (touch.x,touch.y)
        touch.grab(self)
        if len(self._touches) == 1:
            self._pinch_finished = False
            self._inspect(touch.x)
        else:
            first, second = [self._positions[item.uid] for item in self._touches]
            midpoint = (first[0]+second[0])/2
            distance = math.dist(first,second)
            self._pinch = dict(bounds=self.viewport.bounds,anchor=self._index_at_x(midpoint),
                               distance=max(dp(12),distance),log_scale=0.,midpoint=midpoint,
                               ready=distance>=dp(12))
            self._smooth_limits = True
            self._pinch_clock = Clock.schedule_interval(self._advance_pinch,0)
            self.inspection = None
        self.redraw()
        return True

    def on_touch_move(self, touch):
        if touch in self._touches:
            if touch.grab_current is self:
                # Store both samples in chart coordinates. Another touch object's
                # current x/y may already have been restored to window coordinates.
                self._positions[touch.uid] = (touch.x,touch.y)
                if len(self._touches) == 2 and self._pinch is not None:
                    pass  # One coalesced input/paint update at the next display frame.
                elif not self._pinch_finished:
                    self._inspect(touch.x)
                    self._redraw_trigger()
            return True
        return super().on_touch_move(touch)

    def _advance_pinch(self, dt):
        if self._pinch is None or len(self._touches)!=2:
            return False
        first,second = [self._positions[item.uid] for item in self._touches]
        state = self._pinch
        distance = max(dp(2),math.dist(first,second))
        if not state["ready"]:
            if distance < dp(12):
                return True
            midpoint = (first[0]+second[0])/2
            state.update(distance=distance,anchor=self._index_at_x(midpoint),
                         midpoint=midpoint,ready=True)
            return True
        target = math.log(distance/state["distance"])
        alpha = 1-math.exp(-min(.1,max(1/120,dt))/.04)
        state["log_scale"] += (target-state["log_scale"])*alpha
        state["midpoint"] += ((first[0]+second[0])/2-state["midpoint"])*alpha
        left,_,width,_ = self.plot_rect
        fraction = min(1,max(0,(state["midpoint"]-left)/width))
        self.viewport.pinch(state["bounds"],state["anchor"],fraction,math.exp(state["log_scale"]))
        self._sync_view()
        self.redraw()
        return True

    def on_touch_up(self, touch):
        if touch in self._touches:
            if touch.grab_current is self:
                if self._pinch is not None:
                    self._pinch_finished = True
                    self._pinch = None
                    if self._pinch_clock:
                        self._pinch_clock.cancel()
                        self._pinch_clock = None
                elif not self._pinch_finished:
                    self._inspect(touch.x)
                touch.ungrab(self)
                self._touches.remove(touch)
                self._positions.pop(touch.uid,None)
                self.redraw()
            return True
        return super().on_touch_up(touch)

    def _texture(self,text,color=MUTED):
        key = (text,tuple(color),sp(10))
        if key not in self._textures:
            label = CoreLabel(text=text,font_size=sp(10),color=color)
            label.refresh()
            self._textures[key] = label.texture
            if len(self._textures)>256:
                self._textures.popitem(last=False)
        self._textures.move_to_end(key)
        return self._textures[key]

    def _text(self, text, x, y, color=MUTED, center=False):
        texture = self._texture(text,color)
        width,height = texture.size
        Color(1, 1, 1, 1)
        Rectangle(texture=texture, pos=(x - width / 2 if center else x, y), size=(width, height))

    def redraw(self, *_):
        self.canvas.clear()
        self.axis_ticks = ()
        with self.canvas:
            if not self.prices or not any(p is not None for p in self.prices):
                self._text("No prices loaded. Choose a security to begin.",
                           self.center_x, self.center_y, center=True)
                return
            left, bottom, width, height = self.plot_rect
            limits = self.viewport.y_limits(self.prices, [line.sma for line in self.series])
            if limits is None:
                self._text("No valid prices in this range. Use Zoom out.",
                           self.center_x, self.center_y, center=True)
                return
            low, high = limits
            if self._smooth_limits and self._display_limits:
                old_low,old_high = self._display_limits
                tolerance = max(1e-7,(high-low)*.001)
                if max(abs(old_low-low),abs(old_high-high))>tolerance:
                    low,high = old_low+(low-old_low)*.4,old_high+(high-old_high)*.4
                    if self._pinch is None:
                        self._redraw_trigger()
                elif self._pinch is None:
                    self._smooth_limits = False
            self._display_limits = (low,high)
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
            self.axis_ticks = date_ticks(self.dates,start,end,width,
                                         lambda label:self._texture(label).size[0],dp(10))
            for tick in self.axis_ticks:
                x, _ = point(tick.index, low)
                Color(0.13, 0.18, 0.24, 1)
                Line(points=[x, bottom, x, bottom + height], width=dp(0.5))
                self._text(tick.label,left+tick.center,self.y+dp(20),center=True)
            Color(*MUTED)
            Line(points=[left, bottom + height, left, bottom, left + width, bottom], width=dp(0.6))
            self._text("Date", left + width / 2, self.y, center=True)
            PushMatrix()
            Rotate(angle=90, origin=(self.x + dp(3), bottom + height / 2))
            self._text("Price", self.x + dp(3), bottom + height / 2, center=True)
            PopMatrix()

            def draw_series(values, color, thickness):
                points = []
                Color(*color)
                for index in range(max(0,math.floor(start)), min(math.ceil(end)+1, len(values))):
                    value = values[index]
                    if value is None or not math.isfinite(value):
                        if len(points) >= 4:
                            Line(points=points, width=thickness)
                        points = []
                    else:
                        points.extend(point(index, value))
                if len(points) >= 4:
                    Line(points=points, width=thickness)

            StencilPush()
            Rectangle(pos=(left,bottom),size=(width,height))
            StencilUse()
            draw_series(self.prices, PRICE_COLOR, dp(1.2))
            for index, line in enumerate(self.series):
                color = self.line_color(line, index)
                draw_series(line.sma, color, dp(1.6) if line.active else dp(1))
                for event in self.marker_events[line.key]:
                    if not start <= event.plot_index <= end:
                        continue
                    x, y = point(event.plot_index, event.price)
                    draw_plus(x, y, dp(5), color)
            StencilUnUse()
            Rectangle(pos=(left,bottom),size=(width,height))
            StencilPop()

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
                    caption = f'Date: {info["date"]}\n{self.price_label}: {info["price"]:.4f}\n'
                    caption += f'{self.inspection_name or sma_label(info["period"])}: {sma}' if info["period"] else 'SMA: optimize first'
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
