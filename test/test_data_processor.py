from data.data_processor import DataProcessor

def test_process_market_data():
    raw_data = [{"market": "KRW-BTC"}, {"market": ""}]
    processed = DataProcessor.process_market_data(raw_data)
    assert processed == [{"market": "KRW-BTC"}]

def test_filter_balances():
    raw_balances = [{"currency": "BTC", "balance": "0.5"}, {"currency": "ETH", "balance": "0.0"}]
    filtered = DataProcessor.filter_balances(raw_balances)
    assert filtered == {"BTC": 0.5}
