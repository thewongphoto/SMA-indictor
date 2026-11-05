"""Yahoo adapter and real dated data. Imports yfinance only on an actual request."""
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import math
import threading
import time
import uuid
from zoneinfo import ZoneInfo

from .market_cache import MarketCache
from .market_data import PreviewMarketDataProvider
from .schedule import latest_due
from .securities import Security, SECURITIES, normalize_query, register_security

SCENARIO = "Yahoo EOD"
UTC = timezone.utc


class MarketDataError(RuntimeError):
    pass


def public_error(error):
    if isinstance(error, MarketDataError):
        return str(error)
    text = str(error).lower()
    if "429" in text or "rate" in text and "limit" in text:
        return "Yahoo is limiting requests. Saved data is retained; try again later."
    if "403" in text or "forbidden" in text or "unauthorized" in text or "401" in text:
        return "Yahoo data access was blocked from this device or network. Saved data is retained."
    if "certificate" in text or "ssl" in text:
        return "The secure Yahoo connection failed. Check certificates and device time; saved data is retained."
    if "timeout" in text or "timed out" in text:
        return "Yahoo data request timed out. Saved data is retained."
    if isinstance(error, ImportError):
        return "Install requirements-desktop.txt using the desktop launcher to enable Yahoo data."
    return "Unable to retrieve Yahoo Finance data from this device. Showing saved data when available."


@dataclass(frozen=True)
class HistoricalDataset:
    counter: str
    prices: tuple
    dates: tuple[str, ...]
    currency: str
    timezone: str
    fetched_at: float
    revision: int
    stale: bool = False
    scenario: str = SCENARIO
    version: int = 1
    is_simulated: bool = False
    source: str = "yahoo"

    @property
    def label(self):
        return f"{self.counter} · YAHOO EOD · {self.currency}"


class YFinanceClient:
    """Only this transport layer depends on pandas/yfinance/native libraries."""
    def __init__(self, state_directory):
        import yfinance as yf
        self.yf = yf
        yf.config.debug.hide_exceptions = False
        yf.config.network.retries = 0
        yf.set_tz_cache_location(str(state_directory))

    def search(self, query):
        return self.yf.Search(query, max_results=20, news_count=0, lists_count=0,
                              recommended=0, include_cb=False, include_nav_links=False,
                              include_research=False, include_cultural_assets=False,
                              timeout=10).quotes

    def history(self, symbol, **kwargs):
        ticker = self.yf.Ticker(symbol)
        frame = ticker.history(interval="1d", auto_adjust=False, back_adjust=False,
                               actions=True, repair=False, prepost=False, keepna=True,
                               timeout=10, **kwargs)
        if frame is None or frame.empty:
            raise MarketDataError("Yahoo returned no usable daily observations.")
        mapping = ticker.get_history_metadata()
        # Do not convert the whole lazy mapping: tradingPeriods adds an HTTP call.
        names = ("currency", "exchangeTimezoneName", "exchangeName", "fullExchangeName",
                 "longName", "shortName", "currentTradingPeriod")
        metadata = {key: mapping.get(key) for key in names}
        bars = []
        for stamp, row in frame.iterrows():
            bar = {"date": stamp.date().isoformat()}
            for column, key in (("Open","open"), ("High","high"), ("Low","low"),
                                ("Close","close"), ("Adj Close","adj_close"), ("Volume","volume"),
                                ("Dividends","dividends"), ("Stock Splits","splits")):
                value = row.get(column)
                bar[key] = float(value) if value is not None and math.isfinite(float(value)) else None
            bars.append(bar)
        return bars, metadata


def security_from_quote(quote):
    symbol = str(quote.get("symbol", "")).strip().upper()
    exchange = str(quote.get("exchange", "")).upper()
    kind = str(quote.get("quoteType", "")).upper()
    if not symbol or kind not in {"EQUITY", "ETF"}:
        return None
    if symbol.endswith(".SI") or exchange in {"SES", "SGX"}:
        region, tz, currency = "SG", "Asia/Singapore", "SGD"
    elif exchange in {"NMS", "NGM", "NCM", "NYQ", "ASE", "PCX", "BTS", "NASDAQ", "NYSE", "NYSEARCA"}:
        region, tz, currency = "US", "America/New_York", "USD"
    else:
        return None
    known = next((s for s in SECURITIES if s.ticker == symbol.removesuffix(".SI")), None)
    name = str(quote.get("longname") or quote.get("shortname") or symbol)
    initials = "".join(word[0] for word in name.split()[:2]).upper()
    return Security("YAHOO:" + symbol, symbol, name,
                    str(quote.get("exchDisp") or exchange), initials,
                    known.logo if known else "", provider="yahoo", symbol=symbol,
                    currency=currency, timezone=tz, region=region)


def completed_bars(bars, security, metadata, now):
    """Never use a current in-progress bar as an EOD observation."""
    local = now.astimezone(ZoneInfo(security.timezone))
    session = (metadata.get("currentTradingPeriod") or {}).get("regular", {})
    boundary = session.get("end")
    if isinstance(boundary, (int, float)):
        boundary = datetime.fromtimestamp(boundary, UTC)
    if hasattr(boundary, "to_pydatetime"):
        boundary = boundary.to_pydatetime()
    if not isinstance(boundary, datetime) or boundary.tzinfo is None:
        boundary = None
    # Conservative fallback for the supported equity markets, including SG closing phases.
    hour, minute = (16, 30) if security.region == "US" else (17, 30)
    fallback = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    ready = now >= fallback
    if boundary and boundary.astimezone(local.tzinfo).date() == local.date():
        ready = now >= max(fallback, boundary + timedelta(minutes=15))
    result = {}
    for source in bars:
        item = dict(source)
        day = date.fromisoformat(item["date"])
        if day > local.date() or (day == local.date() and not ready):
            continue
        price = item.get("close")
        if price is not None and (not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0):
            raise MarketDataError("Invalid close in Yahoo response.")
        for key, value in item.items():
            if key != "date" and value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise MarketDataError("Invalid value in Yahoo response.")
        result[item["date"]] = item
    return [result[key] for key in sorted(result)]


class YahooMarketDataProvider:
    is_simulated = False
    scenario = SCENARIO

    def __init__(self, cache: MarketCache, client=None, now=None, client_factory=None):
        self.cache, self._client = cache, client
        self.client_factory = client_factory or YFinanceClient
        self.now = now or (lambda: datetime.now(UTC))
        self._lock = threading.RLock()
        self.last_warning = ""
        self._health_checked = False
        self._health_result = None
        for security in cache.securities():
            register_security(security)

    def initial_dataset(self):
        # Live mode starts without a selected company or any fabricated prices.
        return HistoricalDataset("UNSELECTED", (), (), "", "", 0, 0)

    def _request(self, operation, symbol, function):
        now = self.now().timestamp()
        retry_at = self.cache.preference("yahoo_retry_at", 0)
        if now < retry_at:
            raise MarketDataError("Yahoo requests are paused after rate limiting. "
                                  f"Try again in {math.ceil(retry_at-now)} seconds; saved data remains available.")
        owner = uuid.uuid4().hex
        deadline = time.monotonic() + 45
        while not self.cache.lease("yahoo-network", owner, time.time(), 600):
            if time.monotonic() > deadline:
                raise MarketDataError("Another Yahoo request is still running. Saved data is retained.")
            time.sleep(.15)
        try:
            if self._client is None:
                self._client = self.client_factory(self.cache.path.parent / "yfinance-state")
            value = function(self._client)
            self.cache.operation(operation, symbol, "ok")
            return value
        except Exception as error:
            message = public_error(error)
            if "limiting requests" in message:
                delay = 60.0
                response = getattr(error, "response", None)
                header = getattr(response, "headers", {}).get("Retry-After")
                if header:
                    try:
                        seconds = float(header)
                    except (ValueError, TypeError):
                        try:
                            seconds = parsedate_to_datetime(header).timestamp()-now
                        except (ValueError, TypeError, OverflowError):
                            seconds = 60
                    if math.isfinite(seconds):
                        delay = max(delay, seconds)
                self.cache.set_preference("yahoo_retry_at", now+delay)
            self.cache.operation(operation, symbol, "failed", message)
            raise MarketDataError(message) from None
        finally:
            self.cache.release_lease("yahoo-network", owner)

    def search(self, query, force=False):
        query = normalize_query(query)
        if not query:
            return ()
        with self._lock:
            cached = self.cache.search(query)
            if cached is not None and not force:
                return tuple(register_security(s) for s in cached)
            quotes = self._request("search", query, lambda c: c.search(query))
            matches = {}
            for quote in quotes:
                security = security_from_quote(quote)
                if security:
                    # A search refresh must not downgrade history-verified currency/timezone.
                    security = self.cache.security(security.key) or security
                    matches[security.key] = register_security(security)
            result = tuple(matches.values())
            self.cache.put_search(query, result, self.now().timestamp())
            return result

    def _dataset(self, security, stale=False):
        bars, fetched, revision = self.cache.history(security.key)
        if not bars:
            raise MarketDataError("No downloaded history is available for this security.")
        return HistoricalDataset(security.key, tuple(b.get("close") for b in bars),
                                 tuple(b["date"] for b in bars), security.currency,
                                 security.timezone, fetched, revision, stale)

    def cached_data(self, security):
        _, fetched, _ = self.cache.history(security.key)
        stale = fetched is None or fetched < latest_due(security.region, self.now()).timestamp()
        return self._dataset(security, stale=stale)

    def historical_data(self, security, scenario=None, force=False, full=False, strict=False):
        if security.provider != "yahoo":
            return PreviewMarketDataProvider().historical_data(security, scenario or "Oscillating")
        with self._lock:
            security = self.cache.security(security.key) or security
            old, fetched, _ = self.cache.history(security.key)
            now = self.now()
            self.last_warning = ""
            if old and not force and fetched >= latest_due(security.region, now).timestamp():
                return self._dataset(security)
            kwargs = {"period": "max"}
            if old and not full:
                kwargs = {"start": (date.fromisoformat(old[-1]["date"]) - timedelta(days=10)).isoformat()}
            try:
                bars, metadata = self._request("history-full" if "period" in kwargs else "history-update",
                                              security.symbol, lambda c: c.history(security.symbol, **kwargs))
                tz = metadata.get("exchangeTimezoneName") or security.timezone
                ZoneInfo(tz)  # Reject unrecognized timezone metadata before mutating the cache.
                currency = metadata.get("currency") or security.currency
                if currency not in {"USD", "SGD"}:
                    raise MarketDataError("This desktop preview supports USD and SGD quotations only.")
                identity_change = currency != security.currency or tz != security.timezone
                security = replace(security, timezone=tz, currency=currency,
                                   name=metadata.get("longName") or metadata.get("shortName") or security.name)
                bars = completed_bars(bars, security, metadata, now)
                # An absent final close is not a completed EOD observation.
                while bars and bars[-1].get("close") is None:
                    bars.pop()
                if not bars or (not old and sum(b.get("close") is not None for b in bars) < 4):
                    raise MarketDataError("Yahoo returned insufficient completed daily history.")
                old_by_date = {b["date"]: b for b in old}
                bars = [old_by_date[b["date"]] if b.get("close") is None and
                        old_by_date.get(b["date"], {}).get("close") is not None else b for b in bars]
                correction = any(
                    b["date"] in old_by_date and
                    (b.get("splits") != old_by_date[b["date"]].get("splits") or
                     b.get("adj_close") != old_by_date[b["date"]].get("adj_close") or
                     b.get("close") != old_by_date[b["date"]].get("close") or
                     b.get("dividends") != old_by_date[b["date"]].get("dividends"))
                    for b in bars)
                correction = correction or any(
                    b["date"] not in old_by_date and (b.get("splits") or b.get("dividends")) for b in bars)
                if old and "start" in kwargs and (correction or identity_change):
                    raw, metadata = self._request("history-resync", security.symbol,
                                                 lambda c: c.history(security.symbol, period="max"))
                    bars = completed_bars(raw, security, metadata, now)
                    while bars and bars[-1].get("close") is None:
                        bars.pop()
                    bars = [old_by_date[b["date"]] if b.get("close") is None and
                            old_by_date.get(b["date"], {}).get("close") is not None else b for b in bars]
                    full = True
                if not bars or (old and full and (bars[0]["date"] > old[0]["date"] or
                                                  bars[-1]["date"] < old[-1]["date"] or
                                                  not set(old_by_date).issubset({b["date"] for b in bars}))):
                    raise MarketDataError("Full refresh returned incomplete coverage; previous data is retained.")
                self.cache.merge_history(security, bars, now.timestamp(), replace=bool(full))
                register_security(security)
                return self._dataset(security)
            except Exception as error:
                warning = str(error) if isinstance(error, MarketDataError) else public_error(error)
                self.last_warning = warning
                self.cache.operation("history-result", security.symbol, "stale" if old else "failed", warning)
                if old and not strict:
                    return self._dataset(security, stale=True)
                raise MarketDataError(warning) from None

    def health_check(self, force=False):
        """Once per UI-provider lifetime; explicit Retry/test can force a new operation."""
        with self._lock:
            if self._health_checked and not force:
                return self._health_result
            self._health_checked = True
            try:
                bars, _ = self._request("health", "SPY", lambda c: c.history("SPY", period="5d"))
                if not bars or not any(b.get("close") is not None for b in bars):
                    raise MarketDataError("The availability check returned no usable observations.")
                if max(date.fromisoformat(b["date"]) for b in bars) < self.now().date()-timedelta(days=10):
                    raise MarketDataError("The Yahoo check returned old observations; current availability could not be verified.")
                self._health_result = (True, "")
            except Exception as error:
                self._health_result = (False, str(error) if isinstance(error, MarketDataError) else public_error(error))
                recent = self.cache.operations(1)
                if isinstance(error, MarketDataError) and (not recent or recent[0][3] != "failed"):
                    self.cache.operation("health-result", "SPY", "failed", self._health_result[1])
            return self._health_result
