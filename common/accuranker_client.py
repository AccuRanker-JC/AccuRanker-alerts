"""
Delt klient til AccuRanker API'et. Alle "agenter" (tjek-scripts) i dette repo
bruger denne, så vi kun skal vedligeholde ét sted for autentificering,
pagination og fejlhåndtering.
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
    """Henter alle søgeord for et domæne, med automatisk pagination.

    fields: kommasepareret string, fx
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
        time.sleep(0.5)  # vær pæn overfor rate-limit (100 req/min)

    return keywords
