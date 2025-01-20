import requests
import logging

def safe_request(method, url, headers=None, payload=None):
    """
    Safely performs an HTTP request and handles exceptions.

    Args:
        method (str): HTTP method (GET, POST, etc.).
        url (str): URL for the request.
        headers (dict): Optional headers.
        payload (dict): Optional payload for POST requests.

    Returns:
        dict: JSON response or None if failed.
    """
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=payload, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP Request failed: {e}")
        return None
