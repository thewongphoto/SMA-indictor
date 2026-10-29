"""Native saved-lines bottom sheet with a draggable dismissal handle."""
from kivy.animation import Animation
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget


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


class SavedLinesSheet(FloatLayout):
    """Modal lower sheet. Only attached while visible; chart state stays intact."""
    progress = NumericProperty(0)
    is_open = BooleanProperty(False)

    def __init__(self, host, panel, **kwargs):
        super().__init__(size_hint=(None,None), **kwargs)
        self.host = host
        self.host.bind(pos=self._fit_host, size=self._fit_host)
        self.host.results_footer.bind(height=self._fit_host)
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
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.scroll.add_widget(panel)
        self.body.add_widget(self.scroll)
        self.add_widget(self.body)
        self.bind(pos=self._layout, size=self._layout, progress=self._layout)
        self._fit_host()

    def _fit_host(self, *_):
        # Leave the persistent result navigation accessible, including the
        # same bottom-left button that toggles the sheet closed.
        footer = self.host.results_footer.height
        self.pos = (self.host.x, self.host.y + footer)
        self.size = (self.host.width, max(dp(100), self.host.height-footer))

    def _layout(self, *_):
        self.backdrop.pos, self.backdrop.size = self.pos, self.size
        self.backdrop.background_color = (0, 0, 0, .4*self.progress)
        self.body.size = (min(self.width-dp(16), dp(968)), min(self.height*.7, dp(600)))
        self.body.pos = (self.center_x-self.body.width/2,
                         self.y-self.body.height*(1-self.progress))
        self._background.pos, self._background.size = self.body.pos, self.body.size

    def open(self, *_):
        if self.host.manager.current != "results":
            return
        Animation.cancel_all(self, "progress")
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

    def on_touch_down(self, touch):
        # The dimmed area is modal: no gesture can reach the underlying plot.
        if self.parent is not None and self.collide_point(*touch.pos):
            super().on_touch_down(touch)
            return True
        return False
