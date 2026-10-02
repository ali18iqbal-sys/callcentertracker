"""
api_fetcher.py — Data fetcher for generic HTTP APIs.

Authentication values are resolved through app.utils.secrets, so a token can be
supplied via environment variables or Streamlit Secrets instead of being stored
in the source registry.
"""

import requests
import pandas as pd

from app.utils.secrets import get_api_token


def fetch_api(url, auth_type="none", auth_value=None, json_path=None,
              method="GET", params=None, timeout=60):
    """Fetch a JSON payload from an HTTP API and convert it to a DataFrame.

    Args:
        url: endpoint URL
        auth_type: "none", "bearer" or "api_key"
        auth_value: token/key; falls back to ``API_TOKEN`` / ``API_KEY`` or
            Streamlit Secrets when omitted
        json_path: optional dotted path to the list inside the payload
        method: HTTP method
        params: optional query parameters
        timeout: request timeout in seconds

    Raises:
        ValueError: if the response is not JSON, or the structure is unusable
    """
    headers = {"Accept": "application/json"}
    token = get_api_token(auth_value)

    if auth_type == "bearer" and token:
        headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "api_key" and token:
        headers["X-API-Key"] = token

    response = requests.request(
        method=method.upper(), url=url,
        headers=headers, params=params, timeout=timeout,
    )
    response.raise_for_status()

    try:
        data = response.json()
    except Exception as exc:
        raise ValueError(
            f"The API did not return valid JSON (status {response.status_code})."
        ) from exc

    if json_path and json_path.strip():
        for key in json_path.strip().split("."):
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                raise ValueError(f"Key '{key}' was not found in the JSON path.")

    if isinstance(data, list):
        if not data:
            raise ValueError("The API returned an empty list.")
        return pd.DataFrame(data)

    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list) and value:
                return pd.DataFrame(value)
        return pd.DataFrame([data])

    raise ValueError("The API response structure could not be interpreted.")