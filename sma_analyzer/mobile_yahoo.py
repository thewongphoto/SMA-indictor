"""Portable Yahoo JSON transport for the yfinance search/chart subset.

Implements the same provider contract without importing desktop pandas/curl_cffi
or spawning Python processes. Suitable for Android and a future iOS adapter.
No login, fingerprint rotation, certificate bypass or background polling.
"""
from datetime import datetime, timezone
import math
from pathlib import Path
import time
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo

from .yahoo import MarketDataError
from .version import APP_VERSION

SEARCH = "https://query2.finance.yahoo.com/v1/finance/search"
CHART = "https://query2.finance.yahoo.com/v8/finance/chart/"
COOKIE = "https://fc.yahoo.com"
CRUMB = "https://query1.finance.yahoo.com/v1/test/getcrumb"
UTC = timezone.utc


class YahooHTTPError(MarketDataError):
    def __init__(self, status, response):
        self.status = status
        self.response = response
        super().__init__(f"Yahoo returned HTTP {status}.")


def _number(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise MarketDataError("Yahoo returned a nonnumeric or invalid market observation.")
    return float(value)


def parse_chart(payload):
    """Normalize actual exchange dates, missing values and corporate actions."""
    chart = payload.get("chart", {})
    if chart.get("error"):
        raise MarketDataError("Yahoo returned a symbol/history error. Check the ticker and exchange.")
    results = chart.get("result")
    if not isinstance(results, list) or not results:
        raise MarketDataError("Yahoo returned no daily history.")
    result = results[0]
    metadata = result.get("meta") or {}
    tz_name = metadata.get("exchangeTimezoneName")
    if not tz_name:
        raise MarketDataError("Yahoo did not identify the exchange timezone.")
    try:
        tz = ZoneInfo(tz_name)
    except (ValueError, KeyError):
        raise MarketDataError("Yahoo returned an unrecognized exchange timezone.") from None
    if metadata.get("dataGranularity", "1d") != "1d":
        raise MarketDataError("Yahoo did not return daily observations; history was not replaced.")
    timestamps = result.get("timestamp")
    indicators = result.get("indicators") or {}
    quotes = indicators.get("quote") or []
    if not isinstance(timestamps, list) or not timestamps or not quotes:
        raise MarketDataError("Yahoo returned no daily observations.")
    prices = quotes[0]
    if not isinstance(prices, dict) or len(prices.get("close", [])) != len(timestamps):
        raise MarketDataError("Yahoo returned incomplete price arrays.")
    adjustments = indicators.get("adjclose") or []
    adjusted = adjustments[0].get("adjclose", []) if adjustments else []
    for key in ("open", "high", "low", "volume"):
        if key in prices and len(prices[key]) != len(timestamps):
            raise MarketDataError("Yahoo returned mismatched daily observation arrays.")
    if adjusted and len(adjusted) != len(timestamps):
        raise MarketDataError("Yahoo returned mismatched adjusted-close observations.")

    events = result.get("events") or {}
    dividends, splits = {}, {}
    for event in (events.get("dividends") or {}).values():
        day = datetime.fromtimestamp(event["date"], UTC).astimezone(tz).date().isoformat()
        amount = _number(event.get("amount"))
        if amount is None:
            raise MarketDataError("Yahoo returned an invalid dividend.")
        dividends[day] = dividends.get(day, 0.0) + amount
    for event in (events.get("splits") or {}).values():
        day = datetime.fromtimestamp(event["date"], UTC).astimezone(tz).date().isoformat()
        numerator, denominator = _number(event.get("numerator")), _number(event.get("denominator"))
        if numerator is None or denominator is None or numerator <= 0 or denominator <= 0:
            raise MarketDataError("Yahoo returned an invalid split ratio.")
        splits[day] = splits.get(day, 1.0) * numerator / denominator

    bars = []
    for index, stamp in enumerate(timestamps):
        day = datetime.fromtimestamp(stamp, UTC).astimezone(tz).date().isoformat()
        bar = {"date":day, "adj_close":_number(adjusted[index]) if adjusted else None,
               "dividends":dividends.get(day,0.0), "splits":splits.get(day,0.0)}
        for key in ("open","high","low","close","volume"):
            series = prices.get(key)
            bar[key] = _number(series[index]) if series is not None else None
        bars.append(bar)
    return bars, metadata


class YahooJSONClient:
    """One reusable HTTPS session, with at most one 401 authentication recovery."""
    def __init__(self, state_directory, observer=None, session=None, now=None):
        if session is None:
            import requests
            session = requests.Session()
        self.session = session
        self.session.headers.update({
            # Fixed UA consistent with yfinance's requests backend; no rotation.
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 "
                         f"SMAStockAnalyzer/{APP_VERSION}",
            "Accept":"application/json",
        })
        self.state_directory = Path(state_directory)
        self.observer = observer
        self.now = now or (lambda: datetime.now(UTC))
        self.request_id = ""
        self.symbol = ""
        self.crumb = None

    def begin_operation(self, request_id, operation, symbol):
        self.request_id, self.symbol = request_id, symbol

    def _event(self, url, status, duration, outcome, detail=""):
        if self.observer:
            # Never include query strings, cookies, crumbs, headers or response bodies.
            parsed = urlsplit(url)
            self.observer("http", self.symbol, outcome, detail,
                          request_id=self.request_id, http_status=status,
                          duration_ms=duration, endpoint=parsed.hostname+parsed.path)

    def _get(self, url, parameters=None, allow_status=()):
        started = time.monotonic()
        try:
            response = self.session.get(url, params=parameters, timeout=(6,15),
                                        allow_redirects=False, verify=True)
        except Exception as error:
            name = type(error).__name__.lower()
            detail = ("Secure connection failed." if "ssl" in name else
                      "Request timed out." if "timeout" in name else "Network request failed.")
            self._event(url,None,(time.monotonic()-started)*1000,"failed",detail)
            raise
        status = response.status_code
        accepted = 200 <= status < 300 or status in allow_status
        detail = "Cookie bootstrap may return 404." if status == 404 and status in allow_status else ""
        self._event(url,status,(time.monotonic()-started)*1000,"ok" if accepted else "failed",detail)
        if not accepted:
            raise YahooHTTPError(status,response)
        return response

    def _bootstrap(self):
        self._get(COOKIE, allow_status=(404,))
        response = self._get(CRUMB)
        crumb = response.text.strip()
        if "too many requests" in crumb.lower() or "toomanyrequests" in crumb.lower():
            raise MarketDataError("Yahoo is limiting requests. Saved data is retained; try again later.")
        if not crumb or len(crumb) > 256 or any(c in crumb for c in '<>{}"') or any(c.isspace() for c in crumb):
            raise MarketDataError("Yahoo did not provide a usable anonymous data session.")
        self.crumb = crumb

    def _json(self, url, parameters):
        parameters = dict(parameters)
        if self.crumb:
            parameters["crumb"] = self.crumb
        try:
            response = self._get(url,parameters)
        except YahooHTTPError as error:
            if error.status != 401:
                raise
            # Standard cookie/crumb setup, once. 403/429 are never bypassed/retried.
            self._bootstrap()
            parameters["crumb"] = self.crumb
            response = self._get(url,parameters)
        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError
            return payload
        except (ValueError, TypeError):
            raise MarketDataError("Yahoo returned an invalid data response. Saved data is retained.") from None

    def search(self, query):
        payload = self._json(SEARCH, {"q":query,"quotesCount":20,"newsCount":0,
                                    "listsCount":0,"recommendedCount":0,
                                    "enableFuzzyQuery":"false","enableCb":"false",
                                    "enableNavLinks":"false","enableResearchReports":"false"})
        quotes = payload.get("quotes")
        if not isinstance(quotes,list):
            raise MarketDataError("Yahoo search returned an invalid result. Retry later; cached results are retained.")
        return quotes

    def history(self, symbol, **options):
        parameters = {"interval":"1d","events":"div,splits,capitalGains","includePrePost":"false"}
        if "start" in options:
            tz = ZoneInfo("Asia/Singapore" if symbol.upper().endswith(".SI") else "America/New_York")
            parameters["period1"] = int(datetime.fromisoformat(options["start"]).replace(tzinfo=tz).timestamp())
            parameters["period2"] = int(self.now().timestamp())
        elif options.get("period","max") == "max":
            # Match yfinance's 99-year daily request, then extend to an earlier
            # firstTradeDate if Yahoo advertises one. Never cap MAX to five years.
            parameters["period1"] = int(self.now().timestamp())-3122064000
            parameters["period2"] = int(self.now().timestamp())
        else:
            parameters["range"] = options.get("period","max")
        url = CHART+quote(symbol,safe="")
        payload = self._json(url,parameters)
        bars,metadata = parse_chart(payload)
        first = metadata.get("firstTradeDate")
        if options.get("period","max") == "max" and "start" not in options and isinstance(first,(int,float)) and first < parameters["period1"]:
            parameters["period1"] = int(first)
            bars,metadata = parse_chart(self._json(url,parameters))
        if metadata.get("symbol") and str(metadata["symbol"]).upper() != symbol.upper():
            raise MarketDataError("Yahoo returned a different security's history. The previous cache is retained.")
        return bars,metadata
