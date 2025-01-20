from utils.request_handler import safe_request
from unittest.mock import patch

@patch("requests.get")
def test_safe_request_get(mock_get):
    mock_get.return_value.json.return_value = {"status": "success"}
    mock_get.return_value.raise_for_status = lambda: None
    response = safe_request("GET", "http://example.com")
    assert response == {"status": "success"}

@patch("requests.post")
def test_safe_request_post(mock_post):
    mock_post.return_value.json.return_value = {"status": "success"}
    mock_post.return_value.raise_for_status = lambda: None
    response = safe_request("POST", "http://example.com", payload={"key": "value"})
    assert response == {"status": "success"}
