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
    phone_buy: bool = True
    phone_monitor: bool = True
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
    session_date: str = ""
    source: str = "preview"

    @property
    def key(self) -> str:
        if self.source != "preview":
            return repr((self.source, self.channel, self.kind, self.counter,
                         self.scenario, self.period, self.target, self.session_date))
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
        if line.custom_name:
            subject=f"{line.display_name} · {subject}"
            body=f"{line.display_name} · {body}"
        result.append(Alert(channel, kind, line.counter, line.scenario, line.period,
                            line.target_frequency, session, subject,
                            body + f"\nSIMULATED DATA · {line.scenario} · Session {session}. Research alert only."))
    return tuple(result)


def evaluate_dataset_eod(dataset, line, settings, session=None):
    """Use real session dates for live delivery identity, never shifting indices."""
    from dataclasses import replace
    alerts = evaluate_eod(dataset.prices, line, settings, session)
    if getattr(dataset, "is_simulated", True):
        return alerts
    symbol=dataset.counter.split(":",1)[-1]
    result=[]
    for alert in alerts:
        title="Buy signal" if alert.kind=="buy" else "Impending buy signal"
        movement="crossed above" if alert.kind=="buy" else "closed below"
        result.append(replace(alert,source=dataset.source,session_date=dataset.dates[alert.session-1],
            subject=f"{line.display_name} · {title} for {symbol}",
            body=f"{line.display_name} · {symbol} has {movement} SMA {line.period}, target {line.target_frequency}/year."
                 f"\nAdjusted daily close · {dataset.dates[alert.session-1]} · {dataset.currency}. "
                 "Research signal; not an observed intraday execution."))
    return tuple(result)


class AndroidNotifier:
    """Foreground local Android notifications via python-for-android's Pyjnius.

    Imports Android modules lazily. Requires POST_NOTIFICATIONS permission on
    Android 13+, granted via request_permission(), and a future development build.
    This is local OS delivery, not remote push or a background EOD scheduler.
    """
    def __init__(self,context=None):
        self.context=context
    @staticmethod
    def request_permission(callback=None):
        """Request Android 13+ permission, then call callback once with its result."""
        try:
            from jnius import autoclass
            from android.permissions import check_permission, request_permissions
            sdk = autoclass("android.os.Build$VERSION").SDK_INT
            permission = "android.permission.POST_NOTIFICATIONS"
            if sdk < 33 or check_permission(permission):
                if callback:
                    callback(True)
                return
            from android.runnable import run_on_ui_thread
            def ask():
                request_permissions([permission], lambda _, grants: callback(bool(grants) and all(grants)) if callback else None)
            run_on_ui_thread(ask)()
        except ImportError:
            raise RuntimeError("Phone delivery needs an Android development build. Use Preview on desktop.") from None
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError("Android notification failed. Check device permission and notification setup.") from None

    def send(self, alert: Alert):
        try:
            from jnius import autoclass, cast
            Activity = autoclass("org.kivy.android.PythonActivity")
            Version = autoclass("android.os.Build$VERSION")
            Context = autoclass("android.content.Context")
            activity = self.context or Activity.mActivity
            if activity is None:
                activity=autoclass("org.kivy.android.PythonService").mService
            if activity is None:
                raise RuntimeError("Android notification context is unavailable.")
            manager = cast("android.app.NotificationManager", activity.getSystemService(Context.NOTIFICATION_SERVICE))
            if Version.SDK_INT >= 33 and activity.checkSelfPermission("android.permission.POST_NOTIFICATIONS") != 0:
                raise RuntimeError("Allow notifications in Android settings, then retry the test.")
            if not manager.areNotificationsEnabled():
                raise RuntimeError("Notifications are disabled for this app. Enable them in Android Settings.")
            channel_id = "sma_research_alerts"
            if Version.SDK_INT >= 26:
                Channel = autoclass("android.app.NotificationChannel")
                manager.createNotificationChannel(Channel(channel_id, "SMA research alerts", 3))
                channel = manager.getNotificationChannel(channel_id)
                if channel is not None and channel.getImportance() == 0:
                    raise RuntimeError("SMA alert channel is disabled. Enable it in Android notification settings.")
                builder = autoclass("android.app.Notification$Builder")(activity, channel_id)
            else:
                builder = autoclass("android.app.Notification$Builder")(activity)
            icon = activity.getResources().getIdentifier("ic_stat_sma", "drawable", activity.getPackageName())
            if not icon:
                icon = autoclass("android.R$drawable").stat_notify_more
            builder.setSmallIcon(icon)
            builder.setContentTitle(alert.subject)
            builder.setContentText(alert.body.splitlines()[0])
            builder.setStyle(autoclass("android.app.Notification$BigTextStyle")().bigText(alert.body))
            builder.setAutoCancel(True)
            identifier = int(hashlib.sha256(alert.key.encode()).hexdigest()[:7], 16)
            intent = activity.getPackageManager().getLaunchIntentForPackage(activity.getPackageName())
            if intent is not None:
                PendingIntent = autoclass("android.app.PendingIntent")
                flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                builder.setContentIntent(PendingIntent.getActivity(activity, identifier, intent, flags))
            manager.notify(identifier, builder.build())
        except ImportError:
            raise RuntimeError("Phone delivery needs an Android development build. Use Preview on desktop.") from None
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError("Android notification failed. Check device permission and notification setup.") from None


def alert_log_detail(alert):
    """Controlled signal identity shared by native and foreground delivery logs."""
    title = {"buy": "Buy signal", "monitor": "Impending buy signal", "test": "Test notification"}[alert.kind]
    session = alert.session_date or f"preview session {alert.session}"
    return (f"{title} · {alert.subject} · {alert.channel} · SMA {alert.period} · "
            f"target {alert.target}/year · close {session}.")


def deliver_alerts(store, alerts, phone=None, mailer=None, *, cache=None) -> list[str]:
    """Explicit dispatch with persistent successful-delivery deduplication.

    A failed channel remains retryable. Preview never invokes this function.
    At-most-once per successful local record; a crash after send but before
    recording can cause a repeat. No delivery guarantee or automatic retry.
    """
    report = []
    for alert in alerts:
        detail = alert_log_detail(alert)
        symbol = alert.counter.removeprefix("YAHOO:")
        def record(operation, status, message):
            if cache is not None:
                cache.operation(operation, symbol, status, detail + " " + message)
        if store.was_delivered(alert.key):
            record("notification-delivery", "already_delivered", "Duplicate suppressed; no notification posted.")
            report.append(f"Already delivered: {alert.channel}, session {alert.session}.")
            continue
        record("notification-trigger", "triggered", "Signal matched; attempting delivery.")
        try:
            if alert.channel == "phone":
                (phone or AndroidNotifier()).send(alert)
            else:
                if mailer is None:
                    record("notification-delivery", "not_sent", "Email delivery is unavailable.")
                    report.append("Email not sent. Connect Gmail and press Send enabled alerts.")
                    continue
                mailer.send(alert, store.notification_settings().email)
            store.record_delivery(alert.key)
            status = "Accepted by Gmail" if alert.channel == "email" else "Posted to Android"
            record("notification-delivery", "ok", status + "; OS accepted the notification.")
            report.append(f"{status}: {alert.channel}, session {alert.session}.")
        except (OSError, ValueError, RuntimeError) as error:
            record("notification-delivery", "failed",
                   "Notification was not confirmed. Check OS notification permission/channel and device setup.")
            # Do not expose account details, server replies or secrets in UI logs.
            report.append(f"Delivery failed ({alert.channel}). " + (str(error) if isinstance(error,RuntimeError)
                          else "Check permission, connection and sender setup. Preview remains available."))
    return report
