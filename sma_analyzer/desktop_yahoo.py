"""Desktop-only process boundary around optional native market-data libraries.

A blocked/crashing dependency must not take down the Kivy process. This does not
override an OS security decision; the app reports the failure and retains cache.
Each worker exists only for one user-initiated operation; there is no daemon.
"""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

from .yahoo import MarketDataError, YFinanceClient, public_error


class DesktopYahooClient:
    def __init__(self, state_directory):
        self.state_directory = Path(state_directory)

    def _call(self, operation, **parameters):
        command = [sys.executable, "-m", "sma_analyzer.desktop_yahoo", str(self.state_directory)]
        try:
            result = subprocess.run(command, input=json.dumps(
                {"operation":operation,"parameters":parameters}), text=True,
                capture_output=True, timeout=90, check=False,
                cwd=Path(__file__).resolve().parent.parent)
        except subprocess.TimeoutExpired:
            raise MarketDataError("The Yahoo support process timed out. The app remains open and saved data is retained.") from None
        except OSError:
            raise MarketDataError("The Yahoo support process could not start. Check your Python installation and any OS security alert.") from None
        if result.returncode:
            raise MarketDataError(
                f"The Yahoo support process was stopped (exit {result.returncode}). "
                "If your OS or antivirus displayed an alert, keep the file blocked and "
                "share its exact filename and wording. The app remains open; saved data is retained.")
        try:
            response = json.loads(result.stdout)
            if not isinstance(response, dict) or not isinstance(response.get("ok"), bool):
                raise ValueError
        except (ValueError, TypeError):
            raise MarketDataError("The Yahoo support process returned an invalid response. Saved data is retained.") from None
        if not response["ok"]:
            # Only controlled messages produced by the worker, never captured stderr.
            raise MarketDataError(response.get("message") or "Yahoo could not complete the request.")
        return response["value"]

    def search(self, query):
        return self._call("search", query=query)

    def history(self, symbol, **kwargs):
        bars, metadata = self._call("history", symbol=symbol, options=kwargs)
        return bars, metadata


def _json_value(value):
    if isinstance(value, datetime):
        return value.timestamp()
    raise TypeError("Unsupported market-data value.")


def main():
    try:
        request = json.load(sys.stdin)
        client = YFinanceClient(Path(sys.argv[1]))
        parameters = request["parameters"]
        if request["operation"] == "search":
            value = client.search(parameters["query"])
        elif request["operation"] == "history":
            value = client.history(parameters["symbol"], **parameters["options"])
        elif request["operation"] == "import":
            value = {"yfinance":client.yf.__version__}
        else:
            raise MarketDataError("Unknown data request.")
        response = {"ok":True, "value":value}
    except Exception as error:
        response = {"ok":False, "message":public_error(error)}
    sys.stdout.write(json.dumps(response, default=_json_value, allow_nan=False))


if __name__ == "__main__":
    main()
