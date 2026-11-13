"""Semantic light/dark rendering; chart and brand colours keep their identity."""
from weakref import WeakSet
from kivy.graphics import Color as KivyColor
from kivy.uix.label import Label as KivyLabel
from kivy.uix.button import Button as KivyButton
from . import theme

_objects = WeakSet()
_light = False
_mode = 'dark'
_pairs = [(theme.BG, '#F4F8FA'), (theme.SURFACE, '#FFFFFF'),
          (theme.CONTROL, '#E6EDF1'), (theme.TEXT, '#14232E'),
          (theme.MUTED, '#536875'), (theme.ACCENT, '#007C70'),
          (theme.ON_ACCENT, '#FFFFFF'), (theme.NEGATIVE, '#B52C3B'),
          (theme.BORDER, '#A5B9C4'), (theme.SUNKEN, '#EEF3F6'), (theme.ACCENT_TINT, '#D3F1EC'), (theme.SECONDARY_BAR, '#8DA0AE'), (theme.NEGATIVE_TINT, '#F8DADD'), (theme.WARNING_BG, '#FDF3D7'), (theme.DIVIDER, '#D5DFE5'), (theme.ACCENT_BORDER, '#7CC8BE'), (theme.WARNING_TITLE, '#8A5A00'), (theme.WARNING_TEXT, '#5C4A1E'), (theme.rgba('#DCE5EC'), '#243340')]
# Legacy native surfaces/text are assigned the same semantic roles.
_pairs += [(value, '#E6EDF1') for value in
           [(0.10,.15,.23,1),(.12,.17,.23,1),(.08,.12,.18,1),(.13,.20,.28,1),(.065,.095,.14,1),(.10,.15,.21,1)]]
_pairs += [(value, '#14232E') for value in [(.92,.95,.98,1),(.94,.96,.98,1),(.93,.96,.98,1)]]

def mapped(value):
    if not _light or len(value) != 4 or value[3] == 0:
        return tuple(value)
    for source, target in _pairs:
        if all(abs(a-b)<.002 for a,b in zip(value[:3],source[:3])):
            return (*theme.rgba(target)[:3], value[3])
    return tuple(value)

def refresh_system():
    set_mode(_mode)

def set_mode(mode):
    global _mode, _light
    if mode not in ('system','light','dark'):
        raise ValueError('Unknown appearance')
    _mode = mode
    light = mode == 'light'
    if mode == 'system':
        from kivy.utils import platform
        if platform == 'android':
            try:
                from jnius import autoclass
                config=autoclass('org.kivy.android.PythonActivity').mActivity.getResources().getConfiguration()
                light=(config.uiMode & 0x30)==0x10
            except Exception:
                light=False
    _light=light
    for obj in list(_objects):
        obj.apply_appearance()
    from kivy.core.window import Window
    Window.clearcolor=mapped(theme.BG)

class Color(KivyColor):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._semantic=tuple(KivyColor.rgba.__get__(self))
        _objects.add(self)
        self.apply_appearance()

    @property
    def rgba(self):
        return KivyColor.rgba.__get__(self)

    @rgba.setter
    def rgba(self,value):
        self._semantic=tuple(value)
        self.apply_appearance()

    def apply_appearance(self):
        KivyColor.rgba.__set__(self,mapped(self._semantic))

class TextAppearance:
    def __init__(self,**kwargs):
        self._applying=False
        super().__init__(**kwargs)
        self._semantic_text=tuple(self.color)
        _objects.add(self)
        self.bind(color=self._text_changed)
        self.apply_appearance()

    def _text_changed(self,_,value):
        if not self._applying:
            self._semantic_text=tuple(value)
            self.apply_appearance()

    def apply_appearance(self):
        self._applying=True
        self.color=mapped(self._semantic_text)
        self._applying=False

class Label(TextAppearance,KivyLabel):
    pass

class Button(TextAppearance,KivyButton):
    pass
