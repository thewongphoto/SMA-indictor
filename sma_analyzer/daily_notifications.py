"""One daily check per market slot, shared by native Android/iOS adapters.

No UI, timer, implicit network call, background service or OS import on import.
The native scheduler invokes this job; desktop may use a fixture/manual test.
"""
from dataclasses import replace
from datetime import datetime,timezone,timedelta

from .notifications import evaluate_dataset_eod,evaluate_dataset_start,deliver_alerts,signal_title
from .schedule import latest_due,expected_session_date,job_id
from .line_names import sma_label


def check_detail(line, settings, expected):
    def state(enabled):
        return "On" if enabled else "Off"
    return (f"Saved SMA #{line.id} · {line.display_name} · {sma_label(line.period)} · "
            f"target {line.target_frequency}/year · close {expected}. "
            f"Phone notifications {state(line.push_enabled)}; "
            f"Buy signal {state(settings.phone_buy)} (line {state(line.alert_buy)}); "
            f"Impending buy signal (End of trading) {state(settings.phone_monitor)} (line {state(line.alert_monitor)}); "
            f"Impending buy signal (Start of trading) {state(settings.phone_monitor_start)} (line {state(line.alert_start)}).")


def line_wants(line,settings,phase):
    """Phone switch plus at least one signal type on both globally and for this line.

    End-of-trading slots also run for start-only lines: that closing fetch keeps
    the cache fresh for the following opening reminder.
    """
    if not line.push_enabled:
        return False
    start=settings.phone_monitor_start and line.alert_start
    if phase=="start":
        return start
    return (settings.phone_buy and line.alert_buy) or (settings.phone_monitor and line.alert_monitor) or start


def enabled_lines(store,provider,region=None,phase=None):
    settings=store.notification_settings()
    if not (settings.phone_monitor_start if phase == "start" else
            settings.phone_buy or settings.phone_monitor or settings.phone_monitor_start):
        return []
    result=[]
    for line in store.list_all_lines():
        if not line_wants(line,settings,phase) or not line.counter.startswith("YAHOO:"):
            continue
        security=provider.cache.security(line.counter)
        if security is not None and (region is None or security.region==region):
            result.append((line,security))
    return result


def run_daily_notifications(store,provider,region,notifier,now=None,should_stop=lambda:False,*,phase="end",due_at=None):
    now=now or datetime.now(timezone.utc)
    identifier=job_id(region,phase)
    latest=latest_due(region,now,phase)
    due=latest if due_at is None else datetime.fromtimestamp(due_at,timezone.utc)
    cache=provider.cache
    if due != latest or (phase=="start" and now-due>timedelta(minutes=30)):
        cache.operation("notification-run",identifier,"expired",
            f"{phase.title()}-of-trading slot {due.isoformat()} is no longer current; no API request or late alert.")
        return {"status":"expired","checked":0,"posted":0}
    due=latest  # Keep slot dates/details in Singapore time after validating an explicit UTC timestamp.
    due_at=int(due.timestamp())
    expected=expected_session_date(region,due,phase).isoformat()
    lines=enabled_lines(store,provider,region,phase)
    if not lines:
        cache.operation("notification-run",identifier,"disabled",
            f"Daily slot {due.isoformat()}; no enabled saved SMAs/signal types. No API request or notification.")
        return {"status":"disabled","checked":0,"posted":0}
    if not store.claim_notification_run(identifier,due_at,now.timestamp()):
        cache.operation("notification-run",identifier,"already_checked",
            f"Daily slot {due.isoformat()} already claimed; no repeated API request or notification.")
        return {"status":"already_checked","checked":0,"posted":0}
    cache.operation("notification-run",identifier,"started",f"{phase.title()}-of-trading slot {due.isoformat()}; expected close {expected}.")
    checked,posted,failed=0,0,False
    try:
        groups={}
        for line,security in lines:
            groups.setdefault(security.key,(security,[]))[1].append(line)
        for security,saved_lines in groups.values():
            try:
                if should_stop():
                    raise RuntimeError("The operating system ended this background check.")
                # Shares a fresh interactive cache. A stale/failed download must
                # not create an alert from a previous close.
                data=(provider.cached_data(security) if phase=="start" else provider.historical_data(security,strict=True))
                if data is None:
                    raise ValueError("No complete cached adjusted history for the opening reminder. Open this security or wait for a closing check.")
                # A fresh closing check can confirm that the latest available
                # close predates a weekday holiday. Opening reminders may use
                # that verified last close, but never an old unrefreshed cache.
                verified_older_close=(phase=="start" and data.dates and data.dates[-1]<expected and
                    getattr(data,"fetched_at",0)>=latest_due(region,due).timestamp())
                if not data.dates or data.dates[-1]!=expected and not verified_older_close:
                    for line in saved_lines:
                        cache.operation("notification-check",security.symbol,"no_new_close",
                            check_detail(line,store.notification_settings(),expected) +
                            f" Latest supplied {data.dates[-1] if data.dates else 'none'}. No signal replayed.")
                    continue
                for saved_line in saved_lines:
                    if should_stop():
                        raise RuntimeError("The operating system ended this background check.")
                    try:
                        line=store.get_line(saved_line.id)
                    except ValueError:
                        cache.operation("notification-check",security.symbol,"removed",
                            check_detail(saved_line,store.notification_settings(),expected) +
                            " Saved SMA removed during retrieval; no signal evaluated or notification posted.")
                        continue
                    settings=replace(store.notification_settings(),email_buy=False,email_monitor=False)
                    detail=check_detail(line,settings,expected)
                    if not line_wants(line,settings,phase):
                        cache.operation("notification-check",security.symbol,"disabled",
                            detail + " Switches disabled during retrieval; no signal evaluated or notification posted.")
                        continue
                    checked+=1
                    alerts=(evaluate_dataset_start(data,line,settings,due.date().isoformat(),security.name,region)
                            if phase=="start" else evaluate_dataset_eod(data,line,settings))
                    matches=", ".join(signal_title(alert.kind) for alert in alerts)
                    cache.operation("notification-check",security.symbol,"signal_match" if alerts else "no_signal",
                        detail + (f" Matched: {matches}." if alerts else " No enabled signal triggered at this adjusted close."))
                    for alert in alerts:
                        already_delivered=store.was_delivered(alert.key)
                        deliver_alerts(store,(alert,),phone=notifier,cache=cache)
                        delivered=store.was_delivered(alert.key)
                        if delivered and not already_delivered:
                            posted+=1
                        elif not delivered:
                            failed=True
            except (RuntimeError,ValueError,OSError) as error:
                failed=True
                from .yahoo import public_error
                for line in saved_lines:
                    cache.operation("notification-check",security.symbol,"failed",
                        check_detail(line,store.notification_settings(),expected) + " " + public_error(error))
        status="failed" if failed else "ok"
        detail=f"{checked} enabled SMAs checked; {posted} alerts posted."
        store.finish_notification_run(identifier,due_at,now.timestamp(),status,detail)
        cache.operation("notification-run",identifier,status,detail)
        return {"status":status,"checked":checked,"posted":posted}
    except Exception:
        store.finish_notification_run(identifier,due_at,now.timestamp(),"failed","Daily check interrupted; inspect the request log.")
        cache.operation("notification-run",identifier,"failed","Daily check interrupted; no automatic same-slot replay.")
        raise
