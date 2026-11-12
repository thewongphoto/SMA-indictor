"""Cached-only watchlist summaries; never request data or retune a saved line."""
import math
from .engine import simple_moving_average

def line_state(prices, period):
    if len(prices) < period or not prices or prices[-1] is None:
        return 'Unknown'
    value = simple_moving_average(prices, period)[-1]
    if value is None or not math.isfinite(prices[-1]):
        return 'Unknown'
    return 'Above' if prices[-1] > value else 'Below' if prices[-1] < value else 'On line'

def watchlist(model):
    cards = []
    library = model.library_lines()
    for counter in {line.counter for line in library}:
        security = model.security(counter)
        lines = [line for line in library if line.counter == counter]
        provider = model.data_provider
        try:
            if hasattr(provider, '_dataset'):
                data = provider._dataset(security)
            elif getattr(provider, 'is_simulated', True) is True:
                # Construct local fixtures without invoking a provider retrieval.
                from .market_data import PreviewMarketDataProvider
                data = PreviewMarketDataProvider().historical_data(security, lines[0].scenario)
            else:
                data = None
        except (ValueError, RuntimeError):
            data = None
        prices = data.prices if data else ()
        states = {line.id: line_state(prices, line.period) for line in lines}
        below = sum(value == 'Below' for value in states.values())
        last = prices[-1] if prices and prices[-1] is not None else None
        previous = prices[-2] if len(prices) > 1 else None
        change = (last/previous-1)*100 if last is not None and previous else None
        cards.append(dict(counter=counter, security=security, lines=lines, states=states,
                          below=below, price=last, change=change,
                          currency=getattr(data, 'currency', ''),
                          date=data.dates[-1] if data and data.dates else '',
                          stale=bool(getattr(data, 'stale', False))))
    return sorted(cards, key=lambda card: (not card['below'], card['security'].name.casefold()))
