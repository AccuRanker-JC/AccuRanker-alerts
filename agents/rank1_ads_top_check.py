"""
Agent: Rank 1 with top ads check.

Sends an alert if a keyword reaches rank 1 while Google is also showing an
ad above the organic results for that search (page_serp_features.ads_top).
Only triggers on the transition itself ("condition was false -> condition
is now true"), not every day the condition remains true.

Monitors a DIFFERENT domain than the other agents in this repo - set via
its own repository variable, ACCURANKER_ADS_TOP_DOMAIN_ID.

Required repository variables (Settings -> Secrets and variables -> Actions -> Variables):
  ACCURANKER_ADS_TOP_DOMAIN_ID  - the AccuRanker domain_id to monitor (separate from ACCURANKER_DOMAIN_ID)
  EMAIL_METHOD                   - "resend" or "smtp"
  ALERT_EMAIL_FROM                - sender address

Required secrets (same place, under Secrets) - shared with the other agents:
  ACCURANKER_API_KEY
  ALERT_EMAILS                    - comma-separated list of recipients
  RESEND_API_KEY                  - if EMAIL_METHOD=resend
  SMTP_HOST / SMTP_PORT / SMTP_USERNAME / SMTP_PASSWORD - if EMAIL_METHOD=smtp
"""

import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.accuranker_client import fetch_all_keywords  # noqa: E402
from common.notify import send_email  # noqa: E402

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state", "rank1_ads_top_state.json")
FIELDS = "id,keyword,search_type,ranks.rank,ranks.page_serp_features,ranks.created_at"

SEARCH_TYPE_LABELS = {1: "Desktop", 2: "Mobile"}


def get_latest_rank_info(keyword_obj):
    """Returns (rank, ads_top) from the most recent rank entry."""
    ranks = keyword_obj.get("ranks") or []
    if not ranks:
        return None, False
    latest = max(ranks, key=lambda r: r.get("created_at") or "")
    rank = latest.get("rank")
    features = latest.get("page_serp_features") or {}
    ads_top = bool(features.get("ads_top"))
    return rank, ads_top


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            print(f"WARNING: {STATE_FILE} contained invalid JSON - starting with empty state.")
            return {}
    return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def build_text_body(hits):
    lines = []
    for h in hits:
        lines.append(f"{h['keyword']} ({h['search_type']}) - rank #1, with a top ad shown above it\n")
    return (
        f"{len(hits)} keyword(s) reached rank #1 while a top ad is showing above the organic results:\n\n"
        + "\n".join(lines)
        + "\nCheck AccuRanker for details."
    )


def build_html_body(hits):
    rows = []
    for h in hits:
        rows.append(
            "<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'><strong>{h['keyword']}</strong></td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'>{h['search_type']}</td>"
            "<td style='padding:8px 12px;border-bottom:1px solid #eee;'>#1</td>"
            "<td style='padding:8px 12px;border-bottom:1px solid #eee;'>Yes</td>"
            "</tr>"
        )

    return (
        "<div style='font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222;'>"
        f"<p>{len(hits)} keyword(s) reached rank #1 while a top ad is showing above the organic results:</p>"
        "<table style='border-collapse:collapse;width:100%;'>"
        "<thead><tr>"
        "<th style='text-align:left;padding:8px 12px;border-bottom:2px solid #ccc;'>Keyword</th>"
        "<th style='text-align:left;padding:8px 12px;border-bottom:2px solid #ccc;'>Device</th>"
        "<th style='text-align:left;padding:8px 12px;border-bottom:2px solid #ccc;'>Rank</th>"
        "<th style='text-align:left;padding:8px 12px;border-bottom:2px solid #ccc;'>Top ad shown</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "<p style='margin-top:16px;'>Check AccuRanker for details.</p>"
        "</div>"
    )


def main():
    api_key = os.environ["ACCURANKER_API_KEY"]
    domain_id = os.environ["ACCURANKER_ADS_TOP_DOMAIN_ID"]

    keywords = fetch_all_keywords(api_key, domain_id, FIELDS)
    print(f"Fetched {len(keywords)} keywords from AccuRanker.")

    previous_state = load_state()
    is_first_run = len(previous_state) == 0
    new_state = {}
    hits = []

    for kw in keywords:
        kw_id = str(kw["id"])
        rank, ads_top = get_latest_rank_info(kw)
        condition_now = (rank == 1) and ads_top

        was_condition = previous_state.get(kw_id)  # True / False / None

        if was_condition is False and condition_now is True:
            search_type_label = SEARCH_TYPE_LABELS.get(kw.get("search_type"), "Unknown")
            hits.append({"keyword": kw["keyword"], "search_type": search_type_label})

        new_state[kw_id] = condition_now

    if is_first_run:
        print("First run: saving baseline, not sending any email yet.")
    elif hits:
        text_body = build_text_body(hits)
        html_body = build_html_body(hits)
        send_email(f"AccuRanker: {len(hits)} keyword(s) at rank #1 with a top ad shown", text_body, html_body)
        print(f"Sent alert email for {len(hits)} keyword(s).")
    else:
        print("No changes to report.")

    save_state(new_state)


if __name__ == "__main__":
    main()
