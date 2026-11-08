"""iPhone adapters. Native imports are lazy; data and signal rules stay shared."""
import hashlib
import json
import time
from pathlib import Path

from .android_window import WindowMetrics


def bridge():
    try:
        from pyobjus import autoclass
        return autoclass("SMAIOSBridge").sharedBridge()
    except Exception as error:
        raise RuntimeError("The iPhone native bridge is unavailable. Rebuild using the iOS guide.") from error


def ns_string(value):
    from pyobjus import autoclass
    return autoclass("NSString").stringWithUTF8String_(value.encode("utf-8"))


def native_text(value):
    if not isinstance(value, (str, bytes)):
        value = value.UTF8String()
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def wait_for_foreground():
    """Cold background launch: service native tasks without SDL/OpenGL or Kivy.

    Pump UIKit's main loop briefly, then release the GIL for the native Python
    job. iOS suspends the process after its allowed background work ends. The
    ordinary app UI starts only if the user later brings the app forward.
    """
    native = bridge()
    if not native.isBackground():
        return
    native.start()
    while native.isBackground():
        native.pumpEvents()
        time.sleep(.02)


class IOSWindow:
    """Read UIKit safe/keyboard bounds only while the UI is active."""
    def __init__(self):
        self._event = None
        self._last = None

    def start(self, callback):
        from kivy.clock import Clock
        self.stop()
        self._native = bridge()
        self._native.start()
        def measure(_):
            values = json.loads(native_text(self._native.windowMetricsJSON()))
            metrics = WindowMetrics(**values)
            if metrics != self._last:
                self._last = metrics
                callback(metrics)
        self._last = None
        measure(0)
        self._event = Clock.schedule_interval(measure, .1)

    def stop(self):
        if self._event is not None:
            self._event.cancel()
        self._event = None


class IOSNotifier:
    system_name = "iOS"

    def __init__(self, background_token=None):
        self.background_token = background_token

    @staticmethod
    def request_permission(callback=None):
        from kivy.clock import Clock
        native = bridge()
        native.requestPermission()
        def finished(_):
            result = native.permissionResult()
            if result < 0:
                return True
            if callback:
                callback(bool(result))
            return False
        Clock.schedule_interval(finished, .1)

    def send(self, alert):
        native = bridge()
        if self.background_token and not native.taskActive_(ns_string(self.background_token)):
            raise RuntimeError("iOS ended this background check; no late notification was posted.")
        payload = {"id": hashlib.sha256(alert.key.encode()).hexdigest(),
                   "title": alert.subject, "body": alert.body,
                   "banner": alert.presentation.banner, "sound": alert.presentation.sound,
                   "list": alert.presentation.notification_center,
                   "background_token": self.background_token or ""}
        request = native.postAlertJSON_(ns_string(json.dumps(payload)))
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            result = json.loads(native_text(native.deliveryResult_(request)))
            if result["status"] == "ok":
                return "Banner, sound and Notification Center requested; iOS settings and Focus govern presentation."
            if result["status"] == "failed":
                raise RuntimeError(result["detail"])
            time.sleep(.02)
        raise RuntimeError("iOS did not confirm this notification in time. Check Notification Center and the request log.")


def portable_configuration(config, home=None):
    # iOS may move the sandbox to another UUID during an app update. Persist
    # a path relative to its current home, never the previous container UUID.
    home = Path(home or Path.home()).resolve()
    try:
        relative = Path(config["directory"]).resolve().relative_to(home)
    except ValueError:
        raise RuntimeError("iPhone app data must be stored inside its private application container.") from None
    return dict(config, directory=str(relative), directory_base="application-home")


def configured_directory(config, home=None):
    home = Path(home or Path.home()).resolve()
    directory = (home / config["directory"]).resolve()
    if config.get("directory_base") != "application-home" or not directory.is_relative_to(home):
        raise RuntimeError("Open iPhone Settings in the app to update its background data location.")
    return directory


def sync_ios_schedules(config, cache):
    config = portable_configuration(config)
    result = json.loads(native_text(bridge().configureJSON_(ns_string(json.dumps(config)))))
    cache.operation("notification-scheduler", "iOS", result["status"], result["detail"])
    return result["detail"]


def run_background(region, token):
    """Called by BGTaskScheduler on a native worker, without starting Kivy UI."""
    from .daily_notifications import run_daily_notifications
    from .providers import create_provider
    from .storage import LineStore
    native = bridge()
    config = json.loads(native_text(native.configurationJSON()))
    directory = configured_directory(config)
    provider = create_provider(directory, "ios")
    store = LineStore(directory / "saved_lines.sqlite3")
    stopped = lambda: not native.taskActive_(ns_string(token))
    if region not in config["regions"] or stopped():
        return False
    result = run_daily_notifications(store, provider, region, IOSNotifier(token), should_stop=stopped)
    return result["status"] != "failed" and not stopped()
