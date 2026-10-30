"""Provider boundary for explicit search and history-selection requests.

This release deliberately makes no Twelve Data/network calls. A future provider
can implement these two methods without putting transport work in Kivy widgets.
"""
from .mock_data import Dataset, generate_mock_data
from .securities import search_securities


class PreviewMarketDataProvider:
    is_simulated = True

    def search(self, query):
        return search_securities(query)

    def historical_data(self, security, scenario):
        source = generate_mock_data(security.preview_template, scenario)
        if security.key == source.counter and security.preview_scale == 1:
            return source
        prices = tuple(round(price * security.preview_scale, 4) for price in source.prices)
        return Dataset(security.key, scenario, prices)
