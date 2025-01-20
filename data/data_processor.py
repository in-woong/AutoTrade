class DataProcessor:
    @staticmethod
    def process_market_data(data):
        """
        Processes raw market data for further analysis.

        Args:
            data (list): List of market data.

        Returns:
            list: Processed market data.
        """
        return [item for item in data if item.get("market")]

    @staticmethod
    def filter_balances(balances):
        """
        Filters and processes account balances.

        Args:
            balances (list): List of account balances.

        Returns:
            dict: Processed balance information.
        """
        return {item['currency']: float(item['balance']) for item in balances if float(item['balance']) > 0}
