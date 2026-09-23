"""api_fetcher.py - Custom API se data fetch"""

import requests
import pandas as pd


def fetch_api(url, auth_type="none", auth_value=None, json_path=None,
              method="GET", params=None, timeout=60):
    headers = {"Accept": "application/json"}
    
    if auth_type == "bearer" and auth_value:
        headers["Authorization"] = f"Bearer {auth_value}"
    elif auth_type == "api_key" and auth_value:
        headers["X-API-Key"] = auth_value
    
    response = requests.request(
        method=method.upper(), url=url,
        headers=headers, params=params, timeout=timeout,
    )
    response.raise_for_status()
    
    try:
        data = response.json()
    except Exception:
        raise ValueError(f"API ne JSON return nahi kiya (status {response.status_code})")
    
    if json_path and json_path.strip():
        for key in json_path.strip().split("."):
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                raise ValueError(f"JSON path mein '{key}' nahi mila")
    
    if isinstance(data, list):
        if not data:
            raise ValueError("API ne khali list return ki")
        return pd.DataFrame(data)
    elif isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list) and v:
                return pd.DataFrame(v)
        return pd.DataFrame([data])
    else:
        raise ValueError("Response structure samajh nahi aaya")
