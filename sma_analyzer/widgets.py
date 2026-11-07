"""Small native controls shared by the timeline and the symbol legend."""
import math
from kivy.graphics import Color, Line, Mesh, RoundedRectangle, Triangle, Ellipse
from kivy.core.text import Label as CoreLabel
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, StringProperty, NumericProperty, ListProperty
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.dropdown import DropDown
from kivy.uix.widget import Widget
from kivy.uix.stencilview import StencilView
from kivy.animation import Animation

from .chart import MUTED, draw_plus
from .securities import security_by_key


class PreferenceReveal(StencilView):
    """Clipped, measured disclosure; hidden controls cannot receive touches."""
    progress=NumericProperty(0)

    def __init__(self,body,detach_when_hidden=False,**kwargs):
        super().__init__(size_hint_y=None,height=0,**kwargs)
        self.body=body
        self.detach_when_hidden=detach_when_hidden
        if not detach_when_hidden:
            self.add_widget(body)
        self.bind(pos=self._arrange,width=self._arrange,progress=self._arrange)
        body.bind(minimum_height=self._arrange)
        self._arrange()

    def _arrange(self,*_):
        self.body.size=(self.width,self.body.minimum_height)
        self.height=self.body.height*self.progress
        self.body.pos=(self.x,self.top-self.body.height+dp(10)*(1-self.progress))
        self.body.opacity=self.progress
        self.disabled=self.progress<.999

    def show(self,visible,animate=False):
        Animation.cancel_all(self,"progress")
        if visible and self.body.parent is None:
            self.add_widget(self.body)
        target=1 if visible else 0
        if animate and self.progress!=target:
            animation=Animation(progress=target,duration=.22,t="out_cubic")
            if not visible:
                animation.bind(on_complete=lambda *_:self._detach())
            animation.start(self)
        else:
            self.progress=target
            if not visible:
                self._detach()

    def _detach(self):
        if self.detach_when_hidden and self.progress==0 and self.body.parent is self:
            self.remove_widget(self.body)


class WordEllipsisLabel(Label):
    """One line: omit the overflowing word and everything after it."""
    full_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(halign="left", valign="middle", **kwargs)
        self.bind(width=self._fit_words, height=self._fit_words, full_text=self._fit_words,
                  font_size=self._fit_words, font_name=self._fit_words,
                  bold=self._fit_words, italic=self._fit_words)
        self._fit_words()

    def _fit_words(self, *_):
        self.text_size = (max(0, self.width), self.height)
        measure = CoreLabel(font_name=self.font_name, font_size=self.font_size,
                            bold=self.bold, italic=self.italic).get_extents
        if measure(self.full_text)[0] <= self.width:
            self.text = self.full_text
            return
        words = self.full_text.split()
        while words and measure(" ".join(words) + "…")[0] > self.width:
            words.pop()
        self.text = " ".join(words) + "…" if measure("…")[0] <= self.width else ""


class CompanyLogo(BoxLayout):
    """Packaged brand image, with an offline monogram when none is available."""
    def __init__(self, security, edge=dp(28), **kwargs):
        super().__init__(size_hint=(None, None), size=(edge, edge),
                         pos_hint={"center_y": .5}, padding=edge*.16, **kwargs)
        with self.canvas.before:
            Color(.94, .96, .98, 1)
            self._tile = RoundedRectangle(pos=self.pos, size=self.size, radius=[edge*.22])
        self.bind(pos=self._paint_logo, size=self._paint_logo)
        self.set_security(security)

    def _paint_logo(self, *_):
        self._tile.pos, self._tile.size = self.pos, self.size

    def set_security(self, security):
        self.clear_widgets()
        self.is_fallback = not bool(security.logo_path)
        self.image = (Label(text=security.initials, bold=True, color=(.08,.17,.24,1),
                            font_size=self.width*.38) if self.is_fallback else
                      Image(source=security.logo_path, fit_mode="contain"))
        self.add_widget(self.image)


class SecurityIdentity(BoxLayout):
    """Company logo, whole-word name, and an optionally reserved ticker column."""
    font_size = NumericProperty(sp(13))

    def __init__(self, security, show_ticker=False, logo_size=dp(28), **kwargs):
        defaults = dict(size_hint_y=None, height=dp(44), spacing=dp(8))
        defaults.update(kwargs)
        super().__init__(**defaults)
        self.security = security
        self.logo = CompanyLogo(security, edge=logo_size)
        self.add_widget(self.logo)
        self.name_label = WordEllipsisLabel(full_text=security.name, font_size=self.font_size,
                                            color=(.92,.95,.98,1), bold=True)
        self.add_widget(self.name_label)
        self.ticker_label = None
        if show_ticker:
            self.ticker_label = Label(text=security.ticker, size_hint_x=None, font_size=sp(11),
                                      color=MUTED, halign="right", valign="middle")
            self.ticker_label.bind(texture_size=lambda widget, size:setattr(widget, "width", size[0]+dp(2)))
            self.ticker_label.texture_update()
            self.add_widget(self.ticker_label)
        self.bind(font_size=lambda _, value:setattr(self.name_label, "font_size", value))

    def set_security(self, security):
        self.security = security
        self.logo.set_security(security)
        self.name_label.full_text = security.name
        if self.ticker_label is not None:
            self.ticker_label.text = security.ticker


class SecurityIdentityButton(ButtonBehavior, SecurityIdentity):
    # Keep the selection's stable key separate from its rendered company name.
    text = StringProperty("")

    def __init__(self, text, filled=False, **kwargs):
        super().__init__(security=security_by_key(text), **kwargs)
        self.text = text
        self.filled = filled
        with self.canvas.before:
            self._identity_color = Color(0,0,0,0)
            self._identity_rect = RoundedRectangle(pos=self.pos,size=self.size,radius=[dp(10)])
        self.bind(text=lambda _, key:self.set_security(security_by_key(key)),
                  pos=self._paint_identity, size=self._paint_identity,
                  state=self._paint_identity, disabled=self._paint_identity)
        self._paint_identity()

    def _paint_identity(self, *_):
        self._identity_rect.pos,self._identity_rect.size=self.pos,self.size
        self._identity_color.rgba = ((.16,.25,.30,1) if self.state=="down" else
                                      (.12,.17,.23,1) if self.filled else (0,0,0,0))
        self.opacity = .55 if self.disabled else 1


class SavedSecurityGroup(BoxLayout):
    """One continuous, lightly tinted enclosure for a company and its SMAs."""
    expanded=BooleanProperty(False)
    def __init__(self, expanded=False, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(8),
                         padding=(dp(10),dp(6)), **kwargs)
        self.expanded = expanded
        self.bind(minimum_height=self.setter("height"), pos=self._paint_group, size=self._paint_group,
                  expanded=self._paint_group)
        self._paint_group()

    def _paint_group(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(.18,.32,.35,.48 if self.expanded else .20)
            RoundedRectangle(pos=self.pos,size=self.size,radius=[dp(12)])
            Color(.44,.68,.70,.30 if self.expanded else .12)
            Line(rounded_rectangle=(*self.pos,*self.size,dp(12)),width=dp(.7))
            if self.expanded:
                Line(points=[self.x+dp(10),self.top-dp(54),self.right-dp(10),self.top-dp(54)],width=dp(.6))


class TimelineOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.font_size = sp(13)
        self.height = dp(44)


class AnimatedDropDown(DropDown):
    """Brief fade for selectors; attachment and selection still belong to Kivy."""
    def open(self,widget):
        if self.attach_to is widget and self.parent is not None:
            # A quick reopen during fade-out must not dispatch on_dismiss and
            # reset the spinner's newly reopened state.
            Animation.cancel_all(self,"opacity")
            self._closing=False
            Animation(opacity=1,duration=.14,t="out_cubic").start(self)
            return
        if self.attach_to is not None:
            self.dismiss(animate=False)
        Animation.cancel_all(self,"opacity")
        self.opacity=0
        self._closing=False
        super().open(widget)
        Animation(opacity=1,duration=.14,t="out_cubic").start(self)

    def dismiss(self,*args,animate=True):
        if not animate:
            Animation.cancel_all(self,"opacity")
            self._closing=False
            self._real_dismiss()
        elif not getattr(self,"_closing",False) and self.attach_to is not None:
            self._closing=True
            Animation.cancel_all(self,"opacity")
            animation=Animation(opacity=0,duration=.10,t="out_cubic")
            animation.bind(on_complete=lambda *_:self._real_dismiss())
            animation.start(self)

    def _real_dismiss(self,*args):
        self._closing=False
        super()._real_dismiss(*args)


class RoundedSelector(Spinner):
    """One rounded hit target, including the label and drawn downward arrow."""
    __events__ = ("on_select",)

    def __init__(self, **kwargs):
        defaults = dict(option_cls=TimelineOption, dropdown_cls=AnimatedDropDown, size_hint_y=None,
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
    max_width=NumericProperty(100000)
    def __init__(self, text, color, plus=False):
        super().__init__(size_hint=(None, None), height=dp(24), spacing=dp(3))
        self.add_widget(LegendSymbol(color, plus))
        self.natural_width=CoreLabel(font_size=sp(11)).get_extents(text)[0]+dp(29)
        self.label=WordEllipsisLabel(full_text=text,font_size=sp(11),color=MUTED,size_hint=(None,1))
        self.add_widget(self.label)
        self.bind(max_width=self._fit)
        self._fit()

    def _fit(self,*_):
        self.width=min(self.natural_width,max(dp(29),self.max_width))
        self.label.width=max(0,self.width-dp(29))


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
    elif kind == "search_add":
        # Theme-native magnifier with a small floating plus at the top right.
        Color(.58,.91,.85,1)
        Line(circle=(x-radius*.22,y+radius*.10,radius*.65),width=dp(1.25))
        Line(points=[x+radius*.25,y-radius*.38,x+radius*.8,y-radius*.93],
             width=dp(1.5),cap="round")
        Color(.075,.122,.192,1)
        Ellipse(pos=(x+radius*.25,y+radius*.32),size=(radius*1.12,radius*1.12))
        Color(.58,.91,.85,1)
        Line(points=[x+radius*.81,y+radius*.5,x+radius*.81,y+radius*1.25],
             width=dp(1.1),cap="round")
        Line(points=[x+radius*.44,y+radius*.88,x+radius*1.18,y+radius*.88],
             width=dp(1.1),cap="round")
    elif kind == "edit":
        Line(points=[x-radius*.65,y-radius*.65,x-radius*.48,y-radius*.08,
                     x+radius*.5,y+radius*.9,x+radius*.9,y+radius*.5,
                     x-radius*.08,y-radius*.48,x-radius*.65,y-radius*.65],width=dp(1.1))
        Line(points=[x+radius*.33,y+radius*.72,x+radius*.72,y+radius*.33],width=dp(1))
    elif kind == "palette":
        Line(ellipse=(x-radius,y-radius*.75,radius*2,radius*1.6),width=dp(1.1))
        for dx,dy,ink in ((-.5,.25,(1,.74,.36,1)),(0,.5,(1,.49,.62,1)),(.5,.25,(.42,.76,1,1)),
                          (-.3,-.3,(.60,.84,.42,1))):
            Color(*ink)
            Ellipse(pos=(x+dx*radius-radius*.15,y+dy*radius-radius*.15),size=(radius*.3,radius*.3))
    elif kind in ("gain","loss"):
        Color(*((.22,.94,.43,1) if kind=="gain" else (1,.35,.40,1)))
        direction = 1 if kind=="gain" else -1
        Line(points=[x-radius*.65,y-direction*radius*.55,x-radius*.1,y,
                     x+radius*.65,y+direction*radius*.65],width=dp(1.3),cap="round")
        Line(points=[x+radius*.05,y+direction*radius*.65,
                     x+radius*.65,y+direction*radius*.65,
                     x+radius*.65,y+direction*radius*.05],width=dp(1.3),cap="round")


class ColorOption(Button):
    swatch=ListProperty([1,1,1,1])
    selected=BooleanProperty(False)

    def __init__(self,swatch,selected=False,**kwargs):
        super().__init__(size_hint_y=None,height=dp(70),font_size=sp(11),color=(.92,.95,.98,1),
                         background_normal="",background_down="",background_color=(0,0,0,0),
                         valign="bottom",halign="center",padding=(0,dp(4)),**kwargs)
        self.swatch,self.selected=swatch,selected
        self.bind(pos=self._paint,size=self._paint,swatch=self._paint,selected=self._paint)

    def _paint(self,*_):
        self.text_size=self.size
        x,y,r=self.center_x,self.center_y+dp(8),dp(15)
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.swatch)
            Ellipse(pos=(x-r,y-r),size=(2*r,2*r))
            if self.selected:
                Color(.94,.96,.98,1)
                Line(circle=(x,y,r+dp(4)),width=dp(1.4))
                Color(.07,.10,.15,1)
                Line(points=[x-dp(6),y,x-dp(1),y-dp(4),x+dp(7),y+dp(5)],width=dp(1.5))


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
    kind = StringProperty("info")
    def __init__(self, kind, **kwargs):
        kwargs.setdefault("size_hint",(None,None))
        kwargs.setdefault("size",(dp(24),dp(28)))
        super().__init__(**kwargs)
        self.kind = kind
        self.bind(pos=self._paint, size=self._paint,kind=self._paint)

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


class SecurityMatchButton(ButtonBehavior, BoxLayout):
    """One explicit selection target: packaged logo (or initials), ticker and name."""
    def __init__(self, security, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(76),
                         padding=dp(10), spacing=dp(10), **kwargs)
        self.security = security
        logo_box = BoxLayout(size_hint=(None,None), size=(dp(44),dp(44)), pos_hint={"center_y": .5})
        with logo_box.canvas.before:
            Color(.94,.96,.98,1)
            tile = RoundedRectangle(pos=logo_box.pos, size=logo_box.size, radius=[dp(8)])
        logo_box.bind(pos=lambda widget,value:setattr(tile,"pos",value), size=lambda widget,value:setattr(tile,"size",value))
        self.logo_is_fallback = not bool(security.logo_path)
        self.logo_widget = (Label(text=security.initials, bold=True, color=(.08,.17,.24,1), font_size=sp(16))
                            if self.logo_is_fallback else Image(source=security.logo_path, fit_mode="contain"))
        logo_box.padding = dp(7)
        logo_box.add_widget(self.logo_widget)
        self.add_widget(logo_box)
        words = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(3), pos_hint={"center_y": .5})
        words.bind(minimum_height=words.setter("height"))
        self.ticker_label = Label(text=f"{security.ticker} · {security.exchange}", bold=True,
                                  font_size=sp(13), color=(.94,.97,1,1), halign="left", size_hint_y=None)
        self.name_label = Label(text=security.name, font_size=sp(12), color=MUTED, halign="left", size_hint_y=None)
        for label in (self.ticker_label,self.name_label):
            label.bind(width=lambda widget,width:setattr(widget,"text_size",(width,None)),
                       texture_size=lambda widget,size:setattr(widget,"height",size[1]+dp(2)))
            words.add_widget(label)
        words.bind(height=lambda _,height:setattr(self,"height",max(dp(76),height+dp(20))))
        self.add_widget(words)
        with self.canvas.before:
            self._match_color = Color(.10,.15,.21,1)
            self._match_rect = RoundedRectangle(pos=self.pos,size=self.size,radius=[dp(10)])
        self.bind(pos=self._paint_match,size=self._paint_match,state=self._paint_match,disabled=self._paint_match)

    def _paint_match(self,*_):
        self._match_rect.pos,self._match_rect.size=self.pos,self.size
        self._match_color.rgba=(.16,.27,.31,1) if self.state=="down" else (.10,.15,.21,.5 if self.disabled else 1)
