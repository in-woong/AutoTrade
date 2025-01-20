from api_client import fetch_market_data

def get_markets():
    """Fetch all available markets."""
    return fetch_market_data()
