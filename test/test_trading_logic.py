from trading_logic import trading_logic
from unittest.mock import patch

@patch("data.data_fetcher.DataFetcher.get_market_data")
@patch("ai_model.predictor.Predictor.predict_trade")
@patch("api.order.place_order")
def test_trading_logic(mock_place_order, mock_predict, mock_get_market_data):
    mock_get_market_data.return_value = [{"market": "KRW-BTC"}]
    mock_predict.return_value = "buy"
    mock_place_order.return_value = {"order_id": "12345"}

    trading_logic()

    mock_get_market_data.assert_called_once()
    mock_predict.assert_called_once_with("KRW-BTC")
    mock_place_order.assert_called_once_with("KRW-BTC", "bid", "0.01", "5000")
