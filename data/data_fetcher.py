import logging
from api.market import get_markets
from api.account import get_account_info

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DataFetcher:
    @staticmethod
    def get_market_data():
        """Fetches market data."""
        data = get_markets()
        if not data:
            logging.error("Failed to fetch market data.")
            return None
        return data

    @staticmethod
    def get_account_balances():
        """Fetches account balance data."""
        balances = get_account_info()
        if not balances:
            logging.error("Failed to fetch account balances.")
            return None
        return balances
