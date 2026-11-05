"""Explicit desktop API diagnostic. No scheduler and no notification delivery."""
import argparse
import json

from sma_analyzer.market_cache import MarketCache
from sma_analyzer.paths import data_directory
from sma_analyzer.yahoo import YahooMarketDataProvider, MarketDataError
from sma_analyzer.desktop_yahoo import DesktopYahooClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", help="Optionally submit a company/ticker search.")
    parser.add_argument("--symbol", help="Optionally load a result matching this exact Yahoo symbol.")
    parser.add_argument("--refresh", action="store_true", help="Refresh cached query/history explicitly.")
    args = parser.parse_args()
    cache = MarketCache(data_directory()/"market_data.sqlite3")
    provider = YahooMarketDataProvider(cache,client_factory=DesktopYahooClient)
    ok, warning = provider.health_check()
    report = {"health_ok":ok, "warning":warning, "data_directory":str(cache.path.parent)}
    try:
        if args.query or args.symbol:
            matches = provider.search(args.query or args.symbol, force=args.refresh)
            report["matches"] = [{"symbol":s.symbol,"name":s.name,"exchange":s.exchange} for s in matches]
            if args.symbol:
                security = next((s for s in matches if s.symbol == args.symbol.upper()), None)
                if security is None:
                    raise MarketDataError("That exact symbol was not returned among supported US/SG results.")
                data = provider.historical_data(security, force=args.refresh)
                report["history"] = {"first":data.dates[0], "last":data.dates[-1],
                                     "sessions":len(data.prices), "currency":data.currency,
                                     "stale":data.stale}
    except MarketDataError as error:
        report["error"] = str(error)
    report["recent_operations"] = cache.operations(10)
    print(json.dumps(report, indent=2))
    return 0 if ok and "error" not in report else 1


if __name__ == "__main__":
    raise SystemExit(main())
