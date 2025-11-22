#!/usr/bin/env python3
"""
Script to test all API endpoints
"""
import requests
import json
from datetime import datetime


BASE_URL = "http://localhost:8000"


def print_response(endpoint, response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"Endpoint: {endpoint}")
    print(f"Status: {response.status_code}")
    print(f"{'='*60}")

    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2)[:500])  # First 500 chars
        if len(json.dumps(data)) > 500:
            print("... (truncated)")
    else:
        print(f"Error: {response.text}")


def test_api():
    """Test all API endpoints"""

    print(f"Testing API at {BASE_URL}")
    print(f"Time: {datetime.now()}")

    # Test root endpoint
    endpoint = "/"
    response = requests.get(f"{BASE_URL}{endpoint}")
    print_response(endpoint, response)

    # Test health endpoint
    endpoint = "/api/health"
    response = requests.get(f"{BASE_URL}{endpoint}")
    print_response(endpoint, response)

    # Test all forecasts
    endpoint = "/api/forecasts"
    response = requests.get(f"{BASE_URL}{endpoint}")
    print_response(endpoint, response)

    # Test specific forecast
    endpoint = "/api/forecasts/30d"
    response = requests.get(f"{BASE_URL}{endpoint}")
    print_response(endpoint, response)

    # Test historical data
    endpoint = "/api/historical"
    params = {"days": 10}
    response = requests.get(f"{BASE_URL}{endpoint}", params=params)
    print_response(f"{endpoint}?days=10", response)

    # Test indicators
    endpoint = "/api/indicators"
    response = requests.get(f"{BASE_URL}{endpoint}")
    print_response(endpoint, response)

    # Test indicators summary
    endpoint = "/api/indicators/summary"
    response = requests.get(f"{BASE_URL}{endpoint}")
    print_response(endpoint, response)

    # Test news
    endpoint = "/api/news"
    params = {"limit": 5}
    response = requests.get(f"{BASE_URL}{endpoint}", params=params)
    print_response(f"{endpoint}?limit=5", response)

    # Test news sentiment
    endpoint = "/api/news/sentiment"
    response = requests.get(f"{BASE_URL}{endpoint}")
    print_response(endpoint, response)

    # Test drivers
    endpoint = "/api/drivers"
    response = requests.get(f"{BASE_URL}{endpoint}")
    print_response(endpoint, response)

    # Test drivers summary
    endpoint = "/api/drivers/summary"
    response = requests.get(f"{BASE_URL}{endpoint}")
    print_response(endpoint, response)

    # Test statistics
    endpoint = "/api/statistics"
    response = requests.get(f"{BASE_URL}{endpoint}")
    print_response(endpoint, response)

    print(f"\n{'='*60}")
    print("API Test Complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Is it running on http://localhost:8000?")
    except Exception as e:
        print(f"Error: {e}")