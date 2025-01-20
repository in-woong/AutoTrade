from ai_model.predictor import Predictor

def test_predict_trade():
    assert Predictor.predict_trade("KRW-BTC") == "buy"
    assert Predictor.predict_trade("BTC-ETH") == "sell"
    assert Predictor.predict_trade("USD-ETH") == "hold"
