import requests
import time

class PriceMonitor:
    def __init__(self):
        self.previous_price = None

    def check_price_change(self, market, threshold=0.01):
        """
        Checks if the price of a market has changed beyond a threshold.

        Args:
            market (str): Market identifier.
            threshold (float): Price change threshold (e.g., 0.01 for 1%).

        Returns:
            bool: True if price change exceeds threshold, False otherwise.
        """
        url = f"https://api.upbit.com/v1/ticker?markets={market}"
        response = requests.get(url).json()
        current_price = float(response[0]["trade_price"])

        if self.previous_price is None:
            self.previous_price = current_price
            return False

        price_change = abs(current_price - self.previous_price) / self.previous_price
        self.previous_price = current_price

        return price_change >= threshold
