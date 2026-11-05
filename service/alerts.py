"""Short-lived, headless p4a service hosted by an Android WorkManager job."""
import json
import os
from pathlib import Path
import sys
import traceback


def main():
    arguments=json.loads(os.environ["PYTHON_SERVICE_ARGUMENT"])
    directory=Path(arguments["directory"])
    run_id=arguments["run_id"]
    import uuid
    if str(uuid.UUID(run_id))!=run_id:
        raise ValueError("Invalid job identifier")
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
    from sma_analyzer.providers import create_provider
    from sma_analyzer.storage import LineStore
    from sma_analyzer.notifications import AndroidNotifier
    from sma_analyzer.daily_notifications import run_daily_notifications
    from jnius import autoclass
    context=autoclass("org.kivy.android.PythonService").mService
    provider=create_provider(directory,"android")
    try:
        result=run_daily_notifications(LineStore(directory/"saved_lines.sqlite3"),provider,
            arguments["region"],AndroidNotifier(context=context))
    except Exception:
        traceback.print_exc()
        provider.cache.operation("notification-service",arguments["region"],"failed","Headless check failed; share this log.")
        result={"status":"failed"}
    output=directory/"notification-jobs"/(run_id+".json")
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix(".tmp")
    temporary.write_text(json.dumps(result))
    os.replace(temporary,output)


if __name__=="__main__":
    main()
