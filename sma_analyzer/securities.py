"""Small offline search catalogue for the pre-Twelve-Data UI preview."""
from dataclasses import dataclass
from pathlib import Path
import unicodedata
from .branding import local_logo


@dataclass(frozen=True)
class Security:
    key: str
    ticker: str
    name: str
    exchange: str
    initials: str
    logo: str = ""
    preview_template: str = "DEMO-US"
    preview_scale: float = 1.0
    provider: str = "preview"
    symbol: str = ""
    currency: str = ""
    timezone: str = ""
    region: str = ""
    instrument_type: str = ""
    issuer: str = ""

    @property
    def logo_path(self):
        # Resolve against the current local catalogue, including old cached
        # records whose logo/type fields were empty when originally saved.
        logo=local_logo(self.symbol or self.ticker,self.name,self.instrument_type,self.issuer) or self.logo
        path = Path(__file__).parent / "assets" / "logos" / (logo + ".png")
        return str(path) if logo and path.is_file() else ""


# Real company identities are search examples only. Every history is simulated.
SECURITIES = (
    Security("DEMO-SGX", "DEMO-SGX", "Demo Singapore Holdings", "SGX (fictional)", "SG", preview_template="DEMO-SGX"),
    Security("DEMO-US", "DEMO-US", "Demo United States Industries", "US (fictional)", "US"),
    Security("NASDAQ:AAPL", "AAPL", "Apple Inc.", "NASDAQ", "AP", "apple", preview_scale=1.3),
    Security("NASDAQ:MSFT", "MSFT", "Microsoft Corporation", "NASDAQ", "MS", "microsoft", preview_scale=2.1),
    Security("NASDAQ:GOOGL", "GOOGL", "Alphabet Inc. (Google)", "NASDAQ", "GO", "google", preview_scale=.8),
    Security("NASDAQ:TSLA", "TSLA", "Tesla Inc.", "NASDAQ", "TS", "tesla", preview_scale=1.6),
    Security("NASDAQ:NVDA", "NVDA", "NVIDIA Corporation", "NASDAQ", "NV", "nvidia", preview_scale=.6),
    Security("NASDAQ:NFLX", "NFLX", "Netflix Inc.", "NASDAQ", "NF", "netflix", preview_scale=3.1),
    Security("SGX:D05", "D05", "DBS Group Holdings Ltd", "SGX", "DB", "dbs", preview_template="DEMO-SGX", preview_scale=.35),
    Security("SGX:O39", "O39", "Oversea-Chinese Banking Corporation (OCBC)", "SGX", "OC", preview_template="DEMO-SGX", preview_scale=.15),
    Security("SGX:U11", "U11", "United Overseas Bank Limited", "SGX", "UB", preview_template="DEMO-SGX", preview_scale=.3),
    Security("SGX:C6L", "C6L", "Singapore Airlines Limited", "SGX", "SQ", "singaporeairlines", "DEMO-SGX", .06),
)


_DYNAMIC = {}
UNSELECTED_SECURITY = Security("UNSELECTED", "", "Choose a company", "", "?")


def register_security(security):
    if security.provider == "yahoo":
        _DYNAMIC[security.key] = security
    return security


def security_by_key(key):
    if key == UNSELECTED_SECURITY.key:
        return UNSELECTED_SECURITY
    if key in _DYNAMIC:
        return _DYNAMIC[key]
    security = next((item for item in SECURITIES if item.key == key), None)
    if security is None:
        raise ValueError("Choose a security from the search results.")
    return security


def normalize_query(value):
    if not isinstance(value, str):
        raise ValueError("Enter a ticker or company name.")
    value = " ".join(unicodedata.normalize("NFKC", value).split()).casefold()
    if len(value) > 128:
        raise ValueError("Keep the ticker or company name under 129 characters.")
    return value


def search_securities(query):
    query = normalize_query(query)
    if not query:
        return ()
    words = query.split()
    matches = [item for item in SECURITIES
               if all(word in (item.ticker + " " + item.name).casefold() for word in words)]
    return tuple(sorted(matches, key=lambda item: (
        item.ticker.casefold() != query,
        not item.ticker.casefold().startswith(query),
        not item.name.casefold().startswith(query),
        item.name.casefold(), item.exchange, item.ticker)))
