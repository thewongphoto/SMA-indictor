"""Native scheduling boundary; common job/rules never depend on the OS."""
import json
from .daily_notifications import enabled_lines
from .schedule import schedule_spec


def configuration(store,provider,directory):
    regions=sorted({security.region for _,security in enabled_lines(store,provider)})
    specs={}
    for region in ("US","SG"):
        hour,minute,weekdays=schedule_spec(region)
        specs[region]={"hour":hour,"minute":minute,"weekdays":sorted(weekdays),"timezone":"Asia/Singapore"}
    return {"directory":str(directory),"regions":regions,"schedules":specs}


def sync_schedules(store,provider,platform_name):
    if not hasattr(provider,"cache"):
        return "Scheduled checks apply to saved market-data SMAs."
    config=configuration(store,provider,store.path.parent)
    if platform_name=="android":
        from jnius import autoclass
        bridge=autoclass("org.thewongphoto.smaanalyzer.SmaAlertBridge")
        context=autoclass("org.kivy.android.PythonActivity").mActivity
        status=bridge.configure(context,json.dumps(config))
        error=bridge.takeLastError(context)
        if error:
            event=json.loads(error)
            provider.cache.operation("notification-scheduler","Android","failed",event["detail"],now=event["at"]/1000)
            return event["detail"]+"\n"+status
        return status
    if platform_name=="ios":
        from .ios_runtime import sync_ios_schedules
        return sync_ios_schedules(config,provider.cache)
    return "Desktop: interactive retrieval only. Android checks enabled SMAs at the scheduled Singapore times."
