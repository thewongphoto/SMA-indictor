"""Small native controls shared by the timeline and the symbol legend."""
from kivy.graphics import Color, Line, RoundedRectangle, Triangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.widget import Widget

from .chart import MUTED, draw_plus


class TimelineOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.font_size = sp(13)
        self.height = dp(44)


class TimelineSelector(Spinner):
    """One rounded hit target, including the label and drawn downward arrow."""
    __events__ = ("on_select",)

    def __init__(self, **kwargs):
        super().__init__(text="1Y", option_cls=TimelineOption, size_hint=(None, None),
                         width=dp(100), height=dp(44), font_size=sp(14),
                         background_normal="", background_down="", background_color=(0, 0, 0, 0),
                         halign="left", valign="middle", padding=(dp(14), 0), **kwargs)
        self.bind(pos=self._paint, size=self._paint, state=self._paint, text=self._highlight)
        self._paint()

    def _paint(self, *_):
        self.text_size = (self.width - dp(32), self.height)
        self.canvas.before.clear()
        self.canvas.after.clear()
        with self.canvas.before:
            Color(*( (0.16, 0.23, 0.31, 1) if self.state == "down" else (0.12, 0.17, 0.23, 1)))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        with self.canvas.after:
            Color(0.92, 0.95, 0.98, 1)
            x, y, r = self.right - dp(18), self.center_y, dp(4)
            Triangle(points=[x-r, y+r/2, x+r, y+r/2, x, y-r])

    def _update_dropdown(self, *_):
        super()._update_dropdown()
        self._highlight()

    def _highlight(self, *_):
        for option in self._dropdown.container.children:
            option.background_color = ((0.18, 0.31, 0.34, 1) if option.text == self.text
                                       else (0.12, 0.17, 0.23, 1))

    def _on_dropdown_select(self, instance, data, *args):
        super()._on_dropdown_select(instance, data, *args)
        self.dispatch("on_select", data)

    def on_select(self, value):
        pass


class LegendSymbol(Widget):
    def __init__(self, color, plus=False, **kwargs):
        super().__init__(size_hint=(None, None), size=(dp(26), dp(24)), **kwargs)
        self.ink, self.plus = color, plus
        self.bind(pos=self._paint, size=self._paint)

    def _paint(self, *_):
        self.canvas.clear()
        with self.canvas:
            if self.plus:
                draw_plus(self.center_x, self.center_y, dp(5), self.ink)
            else:
                Color(*self.ink)
                Line(points=[self.x+dp(3), self.center_y, self.right-dp(3), self.center_y], width=dp(1.4))


class LegendItem(BoxLayout):
    def __init__(self, text, color, plus=False):
        super().__init__(size_hint=(None, None), height=dp(24), spacing=dp(3))
        self.add_widget(LegendSymbol(color, plus))
        label = Label(text=text, font_size=sp(11), color=MUTED, size_hint=(None, 1))
        label.bind(texture_size=lambda _, size: self._size_label(label, size))
        self.add_widget(label)

    def _size_label(self, label, size):
        label.width = size[0]
        self.width = label.width + dp(29)
