"""Select platform transport while sharing every data/cache/calculation contract."""
from .market_cache import MarketCache
from .market_data import PreviewMarketDataProvider
from .yahoo import YahooMarketDataProvider


def create_provider(directory, platform_name, source="yahoo"):
    if source == "preview":
        return PreviewMarketDataProvider()
    if source != "yahoo":
        raise ValueError("Choose Yahoo data or the explicit offline preview.")
    cache = MarketCache(directory/"market_data.sqlite3")
    if platform_name in ("android","ios"):
        from .mobile_yahoo import YahooJSONClient
        factory = lambda state: YahooJSONClient(state,observer=cache.operation)
        transport = "Yahoo HTTPS search/chart (mobile; yfinance-compatible subset)"
    else:
        from .desktop_yahoo import DesktopYahooClient
        factory = DesktopYahooClient
        transport = "yfinance desktop support process"
    provider = YahooMarketDataProvider(cache,client_factory=factory)
    provider.transport_name = transport
    return provider
