"""Synthetic Yahoo HTTP fixtures, never shipped in the APK."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from scripts.yahoo_test_data import bars_ending


def chart_payload(bars=None, symbol="AAPL"):
    bars = bars if bars is not None else bars_ending(count=5)
    name = "Asia/Singapore" if symbol.endswith(".SI") else "America/New_York"
    tz = ZoneInfo(name)
    timestamps = [int(datetime.fromisoformat(b["date"]).replace(hour=10,tzinfo=tz).timestamp()) for b in bars]
    events = {"dividends":{},"splits":{}}
    for stamp, bar in zip(timestamps,bars):
        if bar.get("dividends"):
            events["dividends"][str(stamp)] = {"date":stamp,"amount":bar["dividends"]}
        if bar.get("splits"):
            events["splits"][str(stamp)] = {"date":stamp,"numerator":bar["splits"],"denominator":1}
    quote = {key:[bar.get(key) for bar in bars] for key in ("open","high","low","close","volume")}
    return {"chart":{"error":None,"result":[{
        "meta":{"symbol":symbol,"currency":"SGD" if symbol.endswith(".SI") else "USD",
                "exchangeTimezoneName":name,"dataGranularity":"1d"},
        "timestamp":timestamps,"indicators":{"quote":[quote],
        "adjclose":[{"adjclose":[b.get("adj_close") for b in bars]}]},
        "events":events,
    }]}}


class Response:
    def __init__(self,status=200,payload=None,text="",headers=None):
        self.status_code,self.payload,self.text,self.headers = status,payload,text,headers or {}

    def json(self):
        if self.payload is None:
            raise ValueError("not JSON")
        return self.payload


class Session:
    def __init__(self,*responses):
        self.responses=list(responses)
        self.headers={}
        self.calls=[]

    def get(self,url,**kwargs):
        self.calls.append((url,kwargs))
        item=self.responses.pop(0)
        if isinstance(item,Exception):
            raise item
        return item
