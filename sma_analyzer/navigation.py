"""Shared page motion, modal bottom sheets and cancelable calculation feedback."""
from kivy.animation import Animation, AnimationTransition
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.screenmanager import SlideTransition
from kivy.uix.widget import Widget
from .app_logo import CrossingLogoAnimation

from .appearance import Color, Label, Button


class SoftPageTransition(SlideTransition):
    """A short crossfade with a small directional offset, without shader FBOs."""
    def __init__(self,**kwargs):
        kwargs.setdefault("duration",.20)
        super().__init__(**kwargs)

    def on_progress(self,progression):
        progress=AnimationTransition.out_cubic(progression)
        x,y=self.manager.pos
        direction=1 if self.direction=="left" else -1
        self.screen_in.pos=(x+direction*dp(16)*(1-progress),y)
        self.screen_out.pos=(x-direction*dp(8)*progress,y)
        self.screen_in.opacity=progress
        self.screen_out.opacity=1-progress

    def on_complete(self):
        self.screen_in.opacity=self.screen_out.opacity=1
        super().on_complete()


class SheetHandle(Widget):
    """Swiping the handle avoids competing with scrolling the saved-line list."""
    def __init__(self, sheet, **kwargs):
        super().__init__(size_hint_y=None, height=dp(32), **kwargs)
        self.sheet = sheet
        self._touch = None
        self.bind(pos=self._paint, size=self._paint)

    def _paint(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(.58, .66, .75, 1)
            Line(points=[self.center_x-dp(20), self.center_y,
                         self.center_x+dp(20), self.center_y], width=dp(2), cap="round")

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self._touch is None:
            self._touch = touch
            self._start_y = touch.y
            self._start_progress = self.sheet.progress
            Animation.cancel_all(self.sheet, "progress")
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch is self._touch:
            distance = self._start_y - touch.y
            self.sheet.progress = max(0, min(1, self._start_progress-distance/self.sheet.body.height))
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch is self._touch:
            touch.ungrab(self)
            self._touch = None
            if self._start_y-touch.y > dp(48) or self.sheet.progress < .65:
                self.sheet.dismiss()
            else:
                self.sheet.open()
            return True
        return super().on_touch_up(touch)


class BottomSheet(FloatLayout):
    """Modal lower sheet. Only attached while visible; chart state stays intact."""
    progress = NumericProperty(0)
    is_open = BooleanProperty(False)

    def __init__(self, host, panel, title="",height_ratio=.7,results_only=False,**kwargs):
        super().__init__(size_hint=(None,None), **kwargs)
        self.host = host
        self.content=panel
        self.title=title
        self.height_ratio=height_ratio
        self.results_only=results_only
        self._host_bound=False
        self.backdrop = Button(background_normal="", background_down="",
                               background_color=(0, 0, 0, .4))
        self.backdrop.bind(on_release=lambda *_: self.dismiss())
        self.add_widget(self.backdrop)
        self.body = BoxLayout(orientation="vertical", size_hint=(None, None))
        with self.body.canvas.before:
            Color(.065,.095,.14,1)
            self._background = RoundedRectangle(radius=[dp(16)])
        self.handle = SheetHandle(self)
        self.body.add_widget(self.handle)
        if title:
            heading=Label(text=title,bold=True,font_size=sp(16),color=(.92,.95,.98,1),
                          halign="left",valign="middle",size_hint_y=None,height=dp(44),padding=(dp(14),0))
            heading.bind(size=lambda widget,size:setattr(widget,"text_size",size))
            self.body.add_widget(heading)
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.scroll.add_widget(panel)
        self.body.add_widget(self.scroll)
        self.add_widget(self.body)
        self.bind(pos=self._layout, size=self._layout, progress=self._layout)
        self._fit_host()

    def _fit_host(self, *_):
        # Leave the fixed top result toolbar accessible above the overlay.
        footer = self.host.results_footer.height if self.results_only else 0
        self.pos = (self.host.x, self.host.y)
        self.size = (self.host.width, max(dp(100), self.host.height-footer))

    def _layout(self, *_):
        self.backdrop.pos, self.backdrop.size = self.pos, self.size
        self.backdrop.background_color = (0, 0, 0, .4*self.progress)
        self.body.size = (min(self.width-dp(16), dp(968)), min(self.height*self.height_ratio, dp(600)))
        self.body.pos = (self.center_x-self.body.width/2,
                         self.y-self.body.height*(1-self.progress))
        self._background.pos, self._background.size = self.body.pos, self.body.size

    def open(self, *_):
        if self.results_only and self.host.manager.current != "results":
            return
        self.host.finish_editing()
        for child in list(self.host.children):
            if isinstance(child,BottomSheet) and child is not self:
                child.dismiss(animate=False)
        Animation.cancel_all(self, "progress")
        if not self._host_bound:
            self.host.bind(pos=self._fit_host,size=self._fit_host)
            if self.results_only:
                self.host.results_footer.bind(height=self._fit_host)
            self._host_bound=True
        self._fit_host()
        self.is_open = True
        if self.parent is None:
            self.host.add_widget(self)
        Animation(progress=1, duration=.22, t="out_cubic").start(self)

    def dismiss(self, *_, animate=True):
        Animation.cancel_all(self, "progress")
        self.is_open = False
        if not animate:
            self._remove()
            return
        animation = Animation(progress=0, duration=.2, t="out_cubic")
        animation.bind(on_complete=lambda *_: self._remove())
        animation.start(self)

    def _remove(self):
        self.progress = 0
        if self.parent is not None:
            self.parent.remove_widget(self)
        if self._host_bound:
            self.host.unbind(pos=self._fit_host,size=self._fit_host)
            if self.results_only:
                self.host.results_footer.unbind(height=self._fit_host)
            self._host_bound=False

    @property
    def _is_open(self):
        return self.is_open

    def on_touch_down(self, touch):
        # The dimmed area is modal: no gesture can reach the underlying plot.
        if self.parent is not None and self.collide_point(*touch.pos):
            super().on_touch_down(touch)
            return True
        return False


class SavedLinesSheet(BottomSheet):
    def __init__(self,host,panel,**kwargs):
        super().__init__(host,panel,results_only=True,**kwargs)


class OptimizationOverlay(FloatLayout):
    """Modal progress feedback; cancellation is handled by native Back/Escape."""
    def __init__(self,host,**kwargs):
        super().__init__(size_hint=(None,None),**kwargs)
        self.host=host
        with self.canvas.before:
            Color(0.02,0.03,0.04,.66)
            self.scrim=Rectangle()
        self.card=BoxLayout(orientation="vertical",size_hint=(None,None),height=dp(292),
                           padding=dp(16),spacing=dp(8))
        from . import theme
        with self.card.canvas.before:
            Color(*theme.SURFACE)
            self.surface=RoundedRectangle(radius=[dp(20)])
        self.logo=CrossingLogoAnimation()
        self.card.add_widget(self.logo)
        self.card.add_widget(Label(text="Finding your SMA line…",bold=True,font_size=sp(18),color=(.92,.95,.98,1)))
        self.caption=Label(font_size=sp(14),color=theme.MUTED,halign="center",valign="middle")
        self.caption.bind(size=lambda widget,size:setattr(widget,"text_size",size))
        self.card.add_widget(self.caption)
        from .app import LabButton
        self.cancel_button=LabButton(text="Cancel")
        self.cancel_button.fill=theme.SURFACE
        self.cancel_button.font_size=sp(15)
        self.cancel_button.height=dp(48)
        with self.cancel_button.canvas.after:
            Color(*theme.BORDER)
            outline=Line(width=dp(1))
        self.cancel_button.bind(pos=lambda b,_:setattr(outline,"rounded_rectangle",(*b.pos,*b.size,dp(10))),
                                size=lambda b,_:setattr(outline,"rounded_rectangle",(*b.pos,*b.size,dp(10))))
        self.cancel_button.bind(on_release=lambda *_: self.host.cancel_optimization())
        self.card.add_widget(self.cancel_button)
        self.add_widget(self.card)
        self.bind(pos=self._layout,size=self._layout)
        self.card.bind(pos=self._paint_card,size=self._paint_card)

    def _layout(self,*_):
        self.scrim.pos,self.scrim.size=self.pos,self.size
        self.card.width=min(dp(340),max(dp(100),self.width-dp(40)))
        self.card.center=self.center

    def _paint_card(self,*_):
        self.surface.pos,self.surface.size=self.card.pos,self.card.size

    def _fit_host(self,*_):
        self.pos,self.size=self.host.pos,self.host.size

    def show(self,target):
        ticker=""
        try:
            data=self.host.model.dataset
            ticker=self.host.model.security(data.counter).ticker if data.prices else ""
        except Exception:
            ticker=""
        self.caption.text=(f"Matching about {target} upward crossings a year" + (f" for {ticker}." if ticker else "."))
        self._fit_host()
        if self.parent is None:
            self.host.bind(pos=self._fit_host,size=self._fit_host)
            self.host.add_widget(self)
            self.opacity=0
            Animation(opacity=1,duration=.12).start(self)
            self.logo.start()

    def dismiss(self):
        Animation.cancel_all(self)
        self.logo.stop()
        self.host.unbind(pos=self._fit_host,size=self._fit_host)
        if self.parent is not None:
            self.parent.remove_widget(self)

    def on_touch_down(self,touch):
        if self.collide_point(*touch.pos):
            super().on_touch_down(touch)
            return True
        return False
