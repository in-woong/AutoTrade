from api.market import get_markets
from api.account import get_account_info
from api.order import place_order
from unittest.mock import patch

@patch("api_client.fetch_market_data")
def test_get_markets(mock_fetch):
    mock_fetch.return_value = [{"market": "KRW-BTC"}]
    markets = get_markets()
    assert markets == [{"market": "KRW-BTC"}]

@patch("api_client.get_balances")
def test_get_account_info(mock_balances):
    mock_balances.return_value = [{"currency": "BTC", "balance": "0.5"}]
    balances = get_account_info()
    assert balances == [{"currency": "BTC", "balance": "0.5"}]

@patch("api_client.execute_trade")
def test_place_order(mock_trade):
    mock_trade.return_value = {"order_id": "12345"}
    response = place_order("KRW-BTC", "bid", "0.01", "5000")
    assert response == {"order_id": "12345"}
