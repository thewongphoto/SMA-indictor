"""Android system-bar/IME geometry, with no Android imports on desktop."""
from dataclasses import dataclass


@dataclass(frozen=True)
class WindowMetrics:
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0
    keyboard: int = 0
    width: int = 1
    height: int = 1

    def content_bounds(self, width, height):
        """Convert native pixels to Kivy coordinates, counting IME/nav overlap once."""
        sx, sy = width / max(1, self.width), height / max(1, self.height)
        left, right = max(0, self.left * sx), max(0, self.right * sx)
        top = max(0, self.top * sy)
        bottom = max(0, self.bottom * sy, self.keyboard * sy)
        return left, bottom, max(1, width-left-right), max(1, height-top-bottom)


class AndroidWindow:
    def __init__(self):
        self._bridge = None
        self._listener = None

    def start(self, callback):
        from jnius import PythonJavaClass, autoclass, java_method

        class Listener(PythonJavaClass):
            __javainterfaces__ = ["org/thewongphoto/smaanalyzer/AndroidWindowBridge$Listener"]
            __javacontext__ = "app"

            @java_method("(IIIIIII)V")
            def onInsets(self, left, top, right, bottom, keyboard, width, height):
                callback(WindowMetrics(left, top, right, bottom, keyboard, width, height))

        self._listener = Listener()
        self._bridge = autoclass("org.thewongphoto.smaanalyzer.AndroidWindowBridge")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        self._bridge.install(activity, self._listener)

    def stop(self):
        if self._bridge is not None:
            self._bridge.uninstall()
        self._listener = self._bridge = None
