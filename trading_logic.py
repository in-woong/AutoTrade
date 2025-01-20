import logging
from data.data_fetcher import DataFetcher
from ai_model.predictor import Predictor
from api.order import place_order
from data.user_manager import UserManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

user_manager = UserManager()


def trading_logic(user_id):
    """
    Main trading logic that fetches data, analyzes it using AI, and executes trades.
    """
    user_info = user_manager.get_user_info(user_id)
    if not user_info or not user_info[-1]:  # Check if user is active
        logging.info(f"User {user_id} is inactive. Skipping.")
        return

    trading_cycle = user_info[4]  # Assuming 'trading_cycle' is at index 4

    # Fetch market data
    market_data = DataFetcher.get_market_data()
    if not market_data:
        logging.error("No market data available.")
        return

    # Example: Analyze the first market in the list
    market = market_data[0]['market']
    logging.info(f"Analyzing market: {market}")

    # Predict trade action
    prediction = Predictor.predict_trade(market)

    # Execute trade based on prediction
    if prediction == "buy":
        logging.info(f"Buying in market: {market}")
        place_order(market, "bid", "0.01", "5000")  # Example values
    elif prediction == "sell":
        logging.info(f"Selling in market: {market}")
        place_order(market, "ask", "0.01", "5100")  # Example values
    else:
        logging.info(f"Holding position in market: {market}")
