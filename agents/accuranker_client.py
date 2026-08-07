"""
Shared client for the AccuRanker API. All "agents" (check scripts) in this
repo use this, so we only need to maintain authentication, pagination, and
error handling in one place.
"""

import time
import requests

API_BASE = "https://app.accuranker.com/api/v4"


def _headers(api_key):
    return {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }


def fetch_all_keywords(api_key, domain_id, fields):
    """Fetches all keywords for a domain, with automatic pagination.

    fields: comma-separated string, e.g.
        "id,keyword,preferred_landing_page,ranks.landing_page,ranks.created_at"
    """
    keywords = []
    limit = 1000
    offset = 0

    while True:
        url = f"{API_BASE}/domains/{domain_id}/keywords/"
        params = {"fields": fields, "limit": limit, "offset": offset}
        resp = requests.post(url, headers=_headers(api_key), params=params, json={}, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        batch = data if isinstance(data, list) else data.get("results", [])
        keywords.extend(batch)

        if len(batch) < limit:
            break
        offset += limit
        time.sleep(0.5)  # be polite towards the rate limit (100 req/min)

    return keywords
