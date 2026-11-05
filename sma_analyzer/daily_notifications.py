"""One daily check per market slot, shared by native Android/iOS adapters.

No UI, timer, implicit network call, background service or OS import on import.
The native scheduler invokes this job; desktop may use a fixture/manual test.
"""
from dataclasses import replace
from datetime import datetime,timezone

from .notifications import evaluate_dataset_eod,deliver_alerts
from .schedule import latest_due,expected_session_date


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
    lines=enabled_lines(store,provider,region)
    if not lines:
        return {"status":"disabled","checked":0,"posted":0}
    if not store.claim_notification_run(region,due_at,now.timestamp()):
        return {"status":"already_checked","checked":0,"posted":0}
    cache=provider.cache
    cache.operation("notification-run",region,"started",f"Daily slot {due.isoformat()}; expected close {expected}.")
    checked,posted,failed=0,0,False
    try:
        groups={}
        for line,security in lines:
            groups.setdefault(security.key,(security,[]))[1].append(line.id)
        for security,line_ids in groups.values():
            try:
                # Shares a fresh interactive cache. A stale/failed download must
                # not create an alert from a previous close.
                data=provider.historical_data(security,strict=True)
                if not data.dates or data.dates[-1]!=expected:
                    cache.operation("notification-check",security.symbol,"no_new_close",
                        f"Expected {expected}; latest supplied {data.dates[-1] if data.dates else 'none'}. No signal replayed.")
                    continue
                for line_id in line_ids:
                    try:
                        line=store.get_line(line_id)
                    except ValueError:
                        continue
                    settings=replace(store.notification_settings(),email_buy=False,email_monitor=False)
                    if not line.push_enabled or not (settings.phone_buy or settings.phone_monitor):
                        continue
                    checked+=1
                    alerts=evaluate_dataset_eod(data,line,settings)
                    for alert in alerts:
                        if store.was_delivered(alert.key):
                            continue
                        report=deliver_alerts(store,(alert,),phone=notifier)
                        if store.was_delivered(alert.key):
                            posted+=1
                        else:
                            failed=True
                        cache.operation("notification-delivery",security.symbol,
                            "ok" if store.was_delivered(alert.key) else "failed","; ".join(report))
                cache.operation("notification-check",security.symbol,"ok",f"Checked enabled saved SMAs for {expected}.")
            except (RuntimeError,ValueError,OSError) as error:
                failed=True
                from .yahoo import public_error
                cache.operation("notification-check",security.symbol,"failed",public_error(error))
        status="failed" if failed else "ok"
        detail=f"{checked} enabled SMAs checked; {posted} alerts posted."
        store.finish_notification_run(region,due_at,now.timestamp(),status,detail)
        cache.operation("notification-run",region,status,detail)
        return {"status":status,"checked":checked,"posted":posted}
    except Exception:
        store.finish_notification_run(region,due_at,now.timestamp(),"failed","Daily check interrupted; inspect the request log.")
        cache.operation("notification-run",region,"failed","Daily check interrupted; no automatic same-slot replay.")
        raise
