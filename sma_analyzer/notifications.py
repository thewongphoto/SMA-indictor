"""Pure EOD alert rules and explicit delivery adapters; no scheduler or network on import."""
from dataclasses import dataclass
from email.utils import parseaddr
import hashlib
import math
from typing import TYPE_CHECKING

from .engine import crossover_events, simple_moving_average
from .settings import DATA_VERSION

if TYPE_CHECKING:
    from .storage import SavedLine


@dataclass(frozen=True)
class NotificationSettings:
    email: str = ""
    phone_buy: bool = False
    phone_monitor: bool = False
    email_buy: bool = False
    email_monitor: bool = False


def validate_email(value: str) -> str:
    """Practical address syntax check, not a claim of mailbox verification."""
    value = value.strip()
    if not value:
        return ""
    display, address = parseaddr(value)
    if (display or address != value or any(c.isspace() for c in value)
            or any(c in value for c in "\r\n,;<>") or value.count("@") != 1):
        raise ValueError("Enter a valid email address, such as name@example.com.")
    local, domain = value.rsplit("@", 1)
    if (not local or len(value) > 254 or "." not in domain or domain.startswith(".")
            or domain.endswith(".") or ".." in value):
        raise ValueError("Enter a valid email address, such as name@example.com.")
    return value


@dataclass(frozen=True)
class Alert:
    channel: str
    kind: str
    counter: str
    scenario: str
    period: int
    target: int
    session: int  # one based, identifies one simulated EOD observation
    subject: str
    body: str

    @property
    def key(self) -> str:
        return repr((DATA_VERSION, self.channel, self.kind, self.counter, self.scenario,
                     self.period, self.target, self.session))


def evaluate_eod(prices, line: "SavedLine", settings: NotificationSettings,
                 session: int | None = None) -> tuple[Alert, ...]:
    """Evaluate only the requested close, never replay the entire history.

    Uses the engine's below/equal/above crossing rules, including gap resets.
    Monitor means strictly below (not equal), once per simulated session.
    Visibility does not affect alerts. Both channel and type must be enabled.
    """
    session = len(prices) if session is None else session
    if isinstance(session, bool) or not isinstance(session, int) or not 1 <= session <= len(prices):
        raise ValueError(f"Choose an EOD session between 1 and {len(prices)}.")
    if line.period > session:
        return ()
    values = prices[:session]
    sma = simple_moving_average(values, line.period)
    price, average = values[-1], sma[-1]
    if price is None or average is None or not math.isfinite(price):
        return ()
    events = crossover_events(values, sma)
    crossing = bool(events and events[-1].index == session - 1)
    result = []
    for channel, enabled, buy, monitor in (
        ("phone", line.push_enabled, settings.phone_buy, settings.phone_monitor),
        ("email", line.email_enabled, settings.email_buy, settings.email_monitor),
    ):
        if not enabled:
            continue
        if crossing and buy:
            kind, subject = "buy", f"Buy Signal for {line.counter}"
            body = f"Buy Signal: {line.counter} has crossed above SMA {line.period}, target {line.target_frequency} /year"
        elif price < average and monitor:
            kind, subject = "monitor", f"Impending buy signal for {line.counter}"
            body = f"Monitor: {line.counter} has closed below SMA {line.period}, target {line.target_frequency} /year"
        else:
            continue
        result.append(Alert(channel, kind, line.counter, line.scenario, line.period,
                            line.target_frequency, session, subject,
                            body + f"\nSIMULATED DATA · {line.scenario} · Session {session}. Research alert only."))
    return tuple(result)


class AndroidNotifier:
    """Foreground local Android notifications via python-for-android's Pyjnius.

    Imports Android modules lazily. Requires POST_NOTIFICATIONS permission on
    Android 13+, granted via request_permission(), and a future development build.
    This is local OS delivery, not remote push or a background EOD scheduler.
    """
    @staticmethod
    def request_permission():
        try:
            from android.permissions import request_permissions
            request_permissions(["android.permission.POST_NOTIFICATIONS"])
        except ImportError:
            raise RuntimeError("Phone delivery needs an Android development build. Use Preview on desktop.") from None
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError("Android notification failed. Check device permission and notification setup.") from None

    def send(self, alert: Alert):
        try:
            from jnius import autoclass
            Activity = autoclass("org.kivy.android.PythonActivity")
            Version = autoclass("android.os.Build$VERSION")
            Context = autoclass("android.content.Context")
            activity = Activity.mActivity
            manager = activity.getSystemService(Context.NOTIFICATION_SERVICE)
            if Version.SDK_INT >= 33 and activity.checkSelfPermission("android.permission.POST_NOTIFICATIONS") != 0:
                raise RuntimeError("Allow notifications in Android settings, then retry the test.")
            channel_id = "sma_research_alerts"
            if Version.SDK_INT >= 26:
                Channel = autoclass("android.app.NotificationChannel")
                manager.createNotificationChannel(Channel(channel_id, "SMA research alerts", 3))
                builder = autoclass("android.app.Notification$Builder")(activity, channel_id)
            else:
                builder = autoclass("android.app.Notification$Builder")(activity)
            builder.setSmallIcon(activity.getApplicationInfo().icon)
            builder.setContentTitle(alert.subject)
            builder.setContentText(alert.body.splitlines()[0])
            builder.setStyle(autoclass("android.app.Notification$BigTextStyle")().bigText(alert.body))
            builder.setAutoCancel(True)
            identifier = int(hashlib.sha256(alert.key.encode()).hexdigest()[:7], 16)
            manager.notify(identifier, builder.build())
        except ImportError:
            raise RuntimeError("Phone delivery needs an Android development build. Use Preview on desktop.") from None
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError("Android notification failed. Check device permission and notification setup.") from None


def deliver_alerts(store, alerts, phone=None) -> list[str]:
    """Explicit dispatch with persistent successful-delivery deduplication.

    A failed channel remains retryable. Preview never invokes this function.
    At-most-once per successful local record; a crash after send but before
    recording can cause a repeat. No delivery guarantee or automatic retry.
    """
    report = []
    for alert in alerts:
        if store.was_delivered(alert.key):
            report.append(f"Already delivered: {alert.channel}, session {alert.session}.")
            continue
        try:
            if alert.channel == "phone":
                (phone or AndroidNotifier()).send(alert)
            else:
                report.append("Email preview only; no email was sent.")
                continue
            store.record_delivery(alert.key)
            report.append(f"Delivered: {alert.channel}, session {alert.session}.")
        except (OSError, ValueError, RuntimeError):
            # Do not expose account details, server replies or secrets in UI logs.
            report.append(f"Delivery failed ({alert.channel}). Check Android notification permission/setup; Preview remains available.")
    return report
