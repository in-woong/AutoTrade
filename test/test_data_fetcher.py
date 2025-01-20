from data.data_fetcher import DataFetcher
from unittest.mock import patch

@patch("api.market.get_markets")
def test_get_market_data(mock_markets):
    mock_markets.return_value = [{"market": "KRW-BTC"}]
    data = DataFetcher.get_market_data()
    assert data == [{"market": "KRW-BTC"}]

@patch("api.account.get_account_info")
def test_get_account_balances(mock_balances):
    mock_balances.return_value = [{"currency": "BTC", "balance": "0.5"}]
    balances = DataFetcher.get_account_balances()
    assert balances == [{"currency": "BTC", "balance": "0.5"}]
