"""Draw the actual shared logo paths progressively; no frame-by-frame image IO."""
from pathlib import Path

from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Rectangle, Fbo, ClearColor, ClearBuffers
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.widget import Widget

from .logo_motion import logo_frame

APP_LOGO = Path(__file__).resolve().parent / "assets/app-icon.png"

# Preserve the generated price/SMA paths exactly. Reveal both from left to
# right, with the central white plus appearing only once they reach the cross.
# This uses the same GLES2 texture shader on desktop, Android and iPhone.
REVEAL_FRAGMENT = """$HEADER$
uniform float sweep;
uniform float plus_alpha;
uniform float mark_alpha;
void main(void) {
    vec4 pixel = texture2D(texture0, tex_coord0);
    float reveal = 1.0 - smoothstep(sweep - 0.006, sweep + 0.006, tex_coord0.x);
    float white = smoothstep(0.76, 0.92, min(pixel.r, min(pixel.g, pixel.b)));
    float central = step(abs(tex_coord0.x - 0.5), 0.09) * step(abs(tex_coord0.y - 0.5), 0.09);
    reveal = mix(reveal, plus_alpha, white * central);
    vec3 navy = vec3(0.075, 0.122, 0.192);
    // Keep a steady navy field while the actual coloured strokes draw in.
    // The master has slight background texture; it must not form a wipe edge.
    float ink = smoothstep(0.25, 0.55, max(pixel.r, max(pixel.g, pixel.b)));
    gl_FragColor = vec4(mix(navy, pixel.rgb, ink * reveal * mark_alpha), pixel.a);
}
"""


class CrossingLogoAnimation(Widget):
    elapsed = NumericProperty(0)
    progress = NumericProperty(0)
    plus_opacity = NumericProperty(0)

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(116))
        super().__init__(**kwargs)
        self._motion_event = None
        # Isolate the effect's matrices/colour from a dimmed modal or screenshot
        # FBO. The visible rectangle uses Kivy's ordinary widget projection.
        with self.canvas:
            self.effect = Fbo(size=(256, 256))
        self.effect.shader.fs = REVEAL_FRAGMENT
        if not self.effect.shader.success:
            raise RuntimeError("The app-logo reveal shader could not compile.")
        with self.effect:
            ClearColor(19/255, 31/255, 49/255, 1)
            ClearBuffers()
            Color(1, 1, 1, 1)
            Rectangle(pos=(0, 0), size=self.effect.size, texture=CoreImage(str(APP_LOGO)).texture)
        with self.canvas:
            Color(1, 1, 1, 1)
            self.mark = Rectangle(texture=self.effect.texture)
        self.bind(pos=self._layout, size=self._layout)
        self._frame(0)
        self._layout()

    def _layout(self, *_):
        edge = min(self.width, self.height)
        self.mark.pos = (self.x+(self.width-edge)/2, self.y+(self.height-edge)/2)
        self.mark.size = (edge, edge)

    def _frame(self, elapsed):
        frame = logo_frame(elapsed)
        self.progress, self.plus_opacity = frame.progress, frame.plus_opacity
        # Artwork starts at about x=.14 and ends at x=.86 in the master.
        self.effect["sweep"] = .12 + .76*frame.progress
        # Kivy chooses glUniform1i for Python ints; these GLSL uniforms require
        # glUniform1f even at the fully hidden/visible endpoints 0 and 1.
        self.effect["plus_alpha"] = float(frame.plus_opacity)
        self.effect["mark_alpha"] = float(frame.opacity)
        self.effect.ask_update()
        self.elapsed = elapsed

    def _advance(self, dt):
        self._frame(self.elapsed + max(0, dt))

    def start(self):
        self.stop()
        self._motion_event = Clock.schedule_interval(self._advance, 0)

    def stop(self):
        if self._motion_event is not None:
            self._motion_event.cancel()
            self._motion_event = None
        self._frame(0)
