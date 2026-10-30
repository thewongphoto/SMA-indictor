"""Small native controls shared by the timeline and the symbol legend."""
import math
from kivy.graphics import Color, Line, Mesh, RoundedRectangle, Triangle, Ellipse
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.button import Button
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


class RoundedSelector(Spinner):
    """One rounded hit target, including the label and drawn downward arrow."""
    __events__ = ("on_select",)

    def __init__(self, **kwargs):
        defaults = dict(option_cls=TimelineOption, size_hint_y=None,
                        height=dp(44), font_size=sp(13), color=(0.92, 0.95, 0.98, 1),
                        background_normal="", background_down="", background_color=(0, 0, 0, 0),
                        halign="left", valign="middle", padding=(dp(12), 0),
                        shorten=True, shorten_from="right")
        defaults.update(kwargs)
        super().__init__(**defaults)
        self.bind(pos=self._paint, size=self._paint, state=self._paint, text=self._highlight)
        self._paint()

    def _paint(self, *_):
        self.text_size = (self.width - dp(28), self.height)
        self.canvas.before.clear()
        self.canvas.after.clear()
        with self.canvas.before:
            Color(*( (0.13, 0.20, 0.28, 1) if self.state == "down" else (0.08, 0.12, 0.18, 1)))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            Color(0.22, 0.29, 0.37, 1)
            Line(rounded_rectangle=(*self.pos, *self.size, dp(10)), width=dp(0.7))
        with self.canvas.after:
            Color(0.92, 0.95, 0.98, 1)
            x, y, r = self.right - dp(18), self.center_y, dp(4)
            if isinstance(self, TimelineSelector):
                Triangle(points=[x-r, y+r/2, x+r, y+r/2, x, y-r])
            else:
                Line(points=[x-r, y+r/2, x, y-r/2, x+r, y+r/2], width=dp(1.1))

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


class TimelineSelector(RoundedSelector):
    def __init__(self, **kwargs):
        super().__init__(text="1Y", size_hint_x=None, width=dp(100), **kwargs)


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


def draw_icon(kind, x, y, radius, selected=False):
    """Canvas icons avoid missing heart/emoji glyphs on desktop and Android."""
    Color(*( (0.96, 0.25, 0.32, 1) if selected and kind == "heart" else MUTED))
    if kind == "heart":
        points = []
        for n in range(65):
            t = n * 2 * math.pi / 64
            points.extend((x + radius * 16 * math.sin(t)**3 / 17,
                           y + radius * (13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t)) / 17))
        if selected:
            vertices = [x, y, 0, 0]
            for px, py in zip(points[::2], points[1::2]):
                vertices.extend((px, py, 0, 0))
            Mesh(vertices=vertices, indices=list(range(len(vertices)//4)), mode="triangle_fan")
        Line(points=points, close=True, width=dp(1.2))
    elif kind == "info":
        Line(circle=(x, y, radius*.72), width=dp(1))
        Ellipse(pos=(x-dp(1), y+radius*.25), size=(dp(2), dp(2)))
        Line(points=[x, y+radius*.02, x, y-radius*.35], width=dp(1.1))
    elif kind == "history":
        # Option A: an open circular return arrow, with a clear upper-left
        # arrowhead and simple clock hands. Keep a generous gap at the left.
        points = []
        for n in range(65):
            angle = math.radians(215 + n * 285 / 64)
            points.extend((x + radius*math.cos(angle), y + radius*math.sin(angle)))
        points.extend((x-radius, y+radius*.4))
        Line(points=points, width=dp(1.15), cap="round", joint="round")
        Line(points=[x-radius, y+radius*.95, x-radius, y+radius*.4,
                     x-radius*.45, y+radius*.4],
             width=dp(1.15), cap="round", joint="round")
        Line(points=[x,y+radius*.43,x,y,x+radius*.36,y-radius*.22],
             width=dp(1.15), cap="round", joint="round")
    elif kind == "phone":
        Line(rounded_rectangle=(x-radius*.55,y-radius,radius*1.1,radius*2,dp(2)), width=dp(1))
        Line(points=[x-radius*.2,y-radius*.7,x+radius*.2,y-radius*.7], width=dp(1))
    elif kind == "mail":
        Line(rectangle=(x-radius,y-radius*.7,radius*2,radius*1.4), width=dp(1))
        Line(points=[x-radius,y+radius*.7,x,y-radius*.1,x+radius,y+radius*.7], width=dp(1))
    elif kind == "menu":
        for offset in (-.55, 0, .55):
            Line(points=[x-radius*.8,y+radius*offset,x+radius*.8,y+radius*offset],
                 width=dp(1.2),cap="round")
    elif kind in ("down", "up"):
        direction = 1 if kind == "down" else -1
        Line(points=[x-radius*.65,y+direction*radius*.3,x,y-direction*radius*.35,x+radius*.65,y+direction*radius*.3],
             width=dp(1.3),cap="round",joint="round")
    elif kind == "back":
        Line(points=[x+radius*.1,y+radius*.65,x-radius*.6,y,x+radius*.1,y-radius*.65],
             width=dp(1.2),cap="round",joint="round")
        Line(points=[x-radius*.55,y,x+radius*.8,y],width=dp(1.2),cap="round")
    elif kind == "settings":
        points = []
        for n in range(32):
            angle = n*math.pi/16
            r = radius*(1 if n%4 in (0,1) else .76)
            points.extend((x+r*math.cos(angle),y+r*math.sin(angle)))
        Line(points=points,close=True,width=dp(1.1))
        Line(circle=(x,y,radius*.3),width=dp(1.1))


class IconButton(Button):
    selected = BooleanProperty(False)
    kind = StringProperty("heart")

    def __init__(self, **kwargs):
        super().__init__(text="", size_hint=(None,None), size=(dp(44),dp(44)),
                         background_normal="", background_down="", background_color=(0,0,0,0), **kwargs)
        self.bind(pos=self._paint, size=self._paint, selected=self._paint, kind=self._paint)
        self._paint()

    def _paint(self, *_):
        self.canvas.after.clear()
        with self.canvas.after:
            draw_icon(self.kind, self.center_x, self.center_y, dp(11), self.selected)


class IconSymbol(Widget):
    def __init__(self, kind, **kwargs):
        super().__init__(size_hint=(None,None), size=(dp(24),dp(28)), **kwargs)
        self.kind = kind
        self.bind(pos=self._paint, size=self._paint)

    def _paint(self, *_):
        self.canvas.clear()
        with self.canvas:
            draw_icon(self.kind, self.center_x, self.center_y, dp(8))


class RuleSwitch(Button):
    """Small native canvas switch, with a 44 dp touch target and no font icons."""
    active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(size_hint=(None,None), size=(dp(64),dp(44)),
                         background_normal="", background_down="", background_color=(0,0,0,0), **kwargs)
        self.bind(pos=self._paint,size=self._paint,active=self._paint)
        self._paint()

    def on_release(self):
        self.active = not self.active

    def _paint(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*( (0.18,0.65,0.57,1) if self.active else (0.23,0.29,0.36,1)))
            RoundedRectangle(pos=(self.center_x-dp(24),self.center_y-dp(12)),size=(dp(48),dp(24)),radius=[dp(12)])
            Color(0.93,0.96,0.98,1)
            Ellipse(pos=(self.center_x + dp(3 if self.active else -21),self.center_y-dp(9)),size=(dp(18),dp(18)))
