"""One daily check per market slot, shared by native Android/iOS adapters.

No UI, timer, implicit network call, background service or OS import on import.
The native scheduler invokes this job; desktop may use a fixture/manual test.
"""
from dataclasses import replace
from datetime import datetime,timezone

from .notifications import evaluate_dataset_eod,deliver_alerts
from .schedule import latest_due,expected_session_date


def check_detail(line, settings, expected):
    def state(enabled):
        return "On" if enabled else "Off"
    return (f"Saved SMA #{line.id} · {line.display_name} · SMA {line.period} · "
            f"target {line.target_frequency}/year · close {expected}. "
            f"Phone notifications {state(line.push_enabled)}; "
            f"Buy signal {state(settings.phone_buy)}; Impending buy signal {state(settings.phone_monitor)}.")


def enabled_lines(store,provider,region=None):
    settings=store.notification_settings()
    if not (settings.phone_buy or settings.phone_monitor):
        return []
    result=[]
    for line in store.list_all_lines():
        if not line.push_enabled or not line.counter.startswith("YAHOO:"):
            continue
        security=provider.cache.security(line.counter)
        if security is not None and (region is None or security.region==region):
            result.append((line,security))
    return result


def run_daily_notifications(store,provider,region,notifier,now=None):
    now=now or datetime.now(timezone.utc)
    due=latest_due(region,now)
    due_at=int(due.timestamp())
    expected=expected_session_date(region,due).isoformat()
    cache=provider.cache
    lines=enabled_lines(store,provider,region)
    if not lines:
        cache.operation("notification-run",region,"disabled",
            f"Daily slot {due.isoformat()}; no enabled saved SMAs/signal types. No API request or notification.")
        return {"status":"disabled","checked":0,"posted":0}
    if not store.claim_notification_run(region,due_at,now.timestamp()):
        cache.operation("notification-run",region,"already_checked",
            f"Daily slot {due.isoformat()} already claimed; no repeated API request or notification.")
        return {"status":"already_checked","checked":0,"posted":0}
    cache.operation("notification-run",region,"started",f"Daily slot {due.isoformat()}; expected close {expected}.")
    checked,posted,failed=0,0,False
    try:
        groups={}
        for line,security in lines:
            groups.setdefault(security.key,(security,[]))[1].append(line)
        for security,saved_lines in groups.values():
            try:
                # Shares a fresh interactive cache. A stale/failed download must
                # not create an alert from a previous close.
                data=provider.historical_data(security,strict=True)
                if not data.dates or data.dates[-1]!=expected:
                    for line in saved_lines:
                        cache.operation("notification-check",security.symbol,"no_new_close",
                            check_detail(line,store.notification_settings(),expected) +
                            f" Latest supplied {data.dates[-1] if data.dates else 'none'}. No signal replayed.")
                    continue
                for saved_line in saved_lines:
                    try:
                        line=store.get_line(saved_line.id)
                    except ValueError:
                        cache.operation("notification-check",security.symbol,"removed",
                            check_detail(saved_line,store.notification_settings(),expected) +
                            " Saved SMA removed during retrieval; no signal evaluated or notification posted.")
                        continue
                    settings=replace(store.notification_settings(),email_buy=False,email_monitor=False)
                    detail=check_detail(line,settings,expected)
                    if not line.push_enabled or not (settings.phone_buy or settings.phone_monitor):
                        cache.operation("notification-check",security.symbol,"disabled",
                            detail + " Switches disabled during retrieval; no signal evaluated or notification posted.")
                        continue
                    checked+=1
                    alerts=evaluate_dataset_eod(data,line,settings)
                    matches=", ".join("Buy signal" if alert.kind=="buy" else "Impending buy signal" for alert in alerts)
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
        store.finish_notification_run(region,due_at,now.timestamp(),status,detail)
        cache.operation("notification-run",region,status,detail)
        return {"status":status,"checked":checked,"posted":posted}
    except Exception:
        store.finish_notification_run(region,due_at,now.timestamp(),"failed","Daily check interrupted; inspect the request log.")
        cache.operation("notification-run",region,"failed","Daily check interrupted; no automatic same-slot replay.")
        raise
