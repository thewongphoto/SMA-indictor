"""Synthetic transport fixtures, exclusively for automated Yahoo adapter tests."""
from datetime import date, datetime, timedelta, timezone
import math

NOW = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)


def bars_ending(end=date(2026, 11, 4), count=1700):
    dates = []
    day = end
    while len(dates) < count:
        if day.weekday() < 5:
            dates.append(day.isoformat())
        day -= timedelta(days=1)
    result = []
    for index, day in enumerate(reversed(dates)):
        price = 100 + index*.01 + 5*math.sin(index/9)
        result.append(dict(date=day, close=price, adj_close=price,
                           open=price, high=price+1, low=price-1,
                           volume=1000, splits=0.0, dividends=0.0))
    return result


class FakeYahooClient:
    def __init__(self, bars=None):
        self.bars = bars if bars is not None else bars_ending()
        self.calls = []
        self.failure = None
        self.metadata = {}

    def search(self, query):
        self.calls.append(("search", query, {}))
        if self.failure:
            raise self.failure
        options = [
            dict(symbol="AAPL", longname="Apple Inc.", exchange="NMS", quoteType="EQUITY"),
            dict(symbol="D05.SI", longname="DBS Group Holdings Ltd", exchange="SES", quoteType="EQUITY"),
            dict(symbol="SPY", longname="SPDR S&P 500 ETF Trust", exchange="PCX", quoteType="ETF"),
        ]
        return [item for item in options if query.casefold() in
                (item["symbol"]+" "+item["longname"]).casefold()]

    def history(self, symbol, **kwargs):
        self.calls.append(("history", symbol, kwargs))
        if self.failure:
            raise self.failure
        bars = [dict(b) for b in self.bars]
        if "start" in kwargs:
            bars = [b for b in bars if b["date"] >= kwargs["start"]]
        if kwargs.get("period") == "5d":
            bars = bars[-5:]
        metadata = dict(currency="SGD" if symbol.endswith(".SI") else "USD",
                        exchangeTimezoneName="Asia/Singapore" if symbol.endswith(".SI") else "America/New_York")
        metadata.update(self.metadata)
        return bars, metadata
