from api_client import execute_trade

def place_order(market, side, volume, price):
    """
    Place an order in the market.

    Args:
        market (str): Market identifier.
        side (str): 'bid' for buy, 'ask' for sell.
        volume (str): Amount of the asset.
        price (str): Price of the asset.

    Returns:
        dict: Response from the API.
    """
    return execute_trade(market, side, volume, price)