"""Shared presentation tokens from the approved November design."""
def rgba(value):
    return tuple(int(value[i:i+2], 16)/255 for i in (1, 3, 5)) + (1,)

BG = rgba('#0B1116')
SURFACE = rgba('#131C24')
CONTROL = rgba('#1A2630')
TEXT = rgba('#EEF3F7')
MUTED = rgba('#8DA0AE')
ACCENT = rgba('#2DD4BF')
ON_ACCENT = rgba('#06201C')
POSITIVE = rgba('#34D399')
NEGATIVE = rgba('#F87171')
BORDER = rgba('#2F4150')
SUNKEN = rgba('#0E161D')
ACCENT_TINT = rgba('#0F3B36')
SECONDARY_BAR = rgba('#5B7386')
NEGATIVE_TINT = rgba('#3A1F22')
WARNING_BG = rgba('#2A2412')
DIVIDER = rgba('#1B2730')
ACCENT_BORDER = rgba('#1E4F49')
WARNING_TITLE = rgba('#FBBF24')
WARNING_TEXT = rgba('#E7D9B0')

def register_fonts():
    from pathlib import Path
    from kivy.core.text import LabelBase
    fonts = Path(__file__).parent/'assets/fonts'
    LabelBase.register('Roboto', fn_regular=str(fonts/'Manrope-Regular.ttf'),
                       fn_bold=str(fonts/'Manrope-Bold.ttf'),
                       fn_italic=str(fonts/'Manrope-Regular.ttf'),
                       fn_bolditalic=str(fonts/'Manrope-Bold.ttf'))
