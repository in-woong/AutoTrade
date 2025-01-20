import os

def load_config():
    """
    Loads configuration from environment variables or default values.

    Returns:
        dict: Configuration settings.
    """
    return {
        "API_KEY": os.getenv("UPBIT_API_KEY", "default_key"),
        "API_SECRET": os.getenv("UPBIT_API_SECRET", "default_secret"),
        "BASE_URL": os.getenv("BASE_URL", "https://api.upbit.com/v1"),
    }
