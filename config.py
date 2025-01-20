import os

# Load configurations from environment variables
API_KEY = os.getenv("UPBIT_API_KEY", "default_api_key")
API_SECRET = os.getenv("UPBIT_API_SECRET", "default_api_secret")
BASE_URL = os.getenv("BASE_URL", "https://api.upbit.com/v1")

# Other global configurations (if needed)
DEFAULT_TRADE_AMOUNT = "0.01"  # Example: Default trade amount
DEFAULT_TRADE_PRICE = "5000"  # Example: Default trade price
