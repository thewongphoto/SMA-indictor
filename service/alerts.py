"""Short, headless Python job bound to an Android WorkManager worker."""
import json
import os
from pathlib import Path
import sys
import time
import uuid


def run(arguments, *, provider_factory=None, notifier=None, context=None, now=None):
    directory=Path(arguments["directory"])
    run_id=arguments["run_id"]
    if str(uuid.UUID(run_id))!=run_id:
        raise ValueError("Invalid job identifier")
    output=directory/"notification-jobs"/(run_id+".json")
    cancellation=output.with_suffix(".cancel")
    deadline=time.monotonic()+230
    provider=None
    stage="provider-startup"
    job=arguments.get("job",arguments.get("region","unknown"))
    try:
        from sma_analyzer.providers import create_provider
        provider=(provider_factory or create_provider)(directory,"android")
        provider.cache.operation("notification-service",job,"started","Headless Python service initialized; no UI or live prices.")
        stage="notification-context"
        from sma_analyzer.notifications import AndroidNotifier,Alert
        if notifier is None:
            if context is None:
                from jnius import autoclass
                context=autoclass("org.kivy.android.PythonService").mService
            if context is None:
                raise RuntimeError("Android service context unavailable")
            notifier=AndroidNotifier(context=context)
        if arguments.get("test"):
            stage="background-test-delivery"
            if cancellation.exists() or time.monotonic()>=deadline:
                raise RuntimeError("Background test cancelled")
            provider.cache.operation("notification-test-background","Android","requested","Bound-service notification test; no market API request or trading signal.")
            alert=Alert("phone","test","TEST","Background service test",2,1,1,
                "SMA background notification test","The background notification path is working. No market prices were requested.")
            receipt=notifier.send(alert)
            provider.cache.operation("notification-test-background","Android","ok",
                "Background test posted; OS accepted it. "+(receipt if isinstance(receipt,str) else ""))
            result={"status":"ok","checked":0,"posted":1}
        else:
            stage="signal-check"
            from sma_analyzer.storage import LineStore
            from sma_analyzer.daily_notifications import run_daily_notifications
            from sma_analyzer.schedule import job_details
            region,phase=job_details(job)
            result=run_daily_notifications(LineStore(directory/"saved_lines.sqlite3"),provider,region,notifier,now,
                should_stop=lambda:cancellation.exists() or time.monotonic()>=deadline,
                phase=phase,due_at=arguments.get("due_at"))
        provider.cache.operation("notification-service",job,result["status"],
            f"Headless job finished; {result.get('checked',0)} SMAs checked; {result.get('posted',0)} alerts posted.")
    except Exception as error:
        # Public diagnostics use stage/type, never raw exceptions, arguments,
        # tokens, paths or response bodies. Even a startup failure gets a report.
        result={"status":"failed","checked":0,"posted":0,"stage":stage,"error_type":type(error).__name__}
        if provider is not None:
            try:
                provider.cache.operation("notification-service",job,"failed",
                    f"Headless job failed at {stage}; {type(error).__name__}. Share this log event.")
            except Exception:
                pass
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix(".tmp")
    temporary.write_text(json.dumps(result),encoding="utf-8")
    os.replace(temporary,output)
    return result


def main():
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
    run(json.loads(os.environ["PYTHON_SERVICE_ARGUMENT"]))


if __name__=="__main__":
    main()
