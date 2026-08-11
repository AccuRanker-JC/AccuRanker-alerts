"""
Agent: Top 3 rank drop check.

Sends an alert if a keyword that was ranking in the top 3 (rank <= 3) on a
previous run has dropped out of the top 3 (rank > 3, or not ranking at all)
on this run. Only triggers on the transition itself ("was top 3 -> no longer
top 3"), not for keywords that were already outside the top 3 last time.

Shares the same repository variables/secrets as preferred_url_check.py:
  ACCURANKER_DOMAIN_ID, ACCURANKER_API_KEY, EMAIL_METHOD, ALERT_EMAIL_FROM,
  ALERT_EMAILS, and either RESEND_API_KEY or the SMTP_* secrets.
"""

import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.accuranker_client import fetch_all_keywords  # noqa: E402
from common.notify import send_email  # noqa: E402

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state", "top3_rank_state.json")
FIELDS = "id,keyword,search_type,ranks.rank,ranks.created_at"
TOP_N = 3

SEARCH_TYPE_LABELS = {1: "Desktop", 2: "Mobile"}


def get_latest_rank(keyword_obj):
    ranks = keyword_obj.get("ranks") or []
    if not ranks:
        return None
    latest = max(ranks, key=lambda r: r.get("created_at") or "")
    return latest.get("rank")  # None if not ranking at all


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


def build_text_body(drops):
    lines = []
    for d in drops:
        current = f"#{d['current_rank']}" if d["current_rank"] is not None else "(not ranking at all)"
        lines.append(
            f"{d['keyword']} ({d['search_type']})\n"
            f"  Previous rank: #{d['previous_rank']}\n"
            f"  Current rank:  {current}\n"
        )
    return (
        f"{len(drops)} keyword(s) dropped out of the top {TOP_N}:\n\n"
        + "\n".join(lines)
        + "\nCheck AccuRanker for details."
    )


def build_html_body(drops):
    rows = []
    for d in drops:
        current = f"#{d['current_rank']}" if d["current_rank"] is not None else "(not ranking at all)"
        rows.append(
            "<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'><strong>{d['keyword']}</strong></td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'>{d['search_type']}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'>#{d['previous_rank']}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;color:#c0392b;'>{current}</td>"
            "</tr>"
        )

    return (
        "<div style='font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222;'>"
        f"<p>{len(drops)} keyword(s) dropped out of the top {TOP_N}:</p>"
        "<table style='border-collapse:collapse;width:100%;'>"
        "<thead><tr>"
        "<th style='text-align:left;padding:8px 12px;border-bottom:2px solid #ccc;'>Keyword</th>"
        "<th style='text-align:left;padding:8px 12px;border-bottom:2px solid #ccc;'>Device</th>"
        "<th style='text-align:left;padding:8px 12px;border-bottom:2px solid #ccc;'>Previous rank</th>"
        "<th style='text-align:left;padding:8px 12px;border-bottom:2px solid #ccc;'>Current rank</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "<p style='margin-top:16px;'>Check AccuRanker for details.</p>"
        "</div>"
    )


def main():
    api_key = os.environ["ACCURANKER_API_KEY"]
    domain_id = os.environ["ACCURANKER_DOMAIN_ID"]

    keywords = fetch_all_keywords(api_key, domain_id, FIELDS)
    print(f"Fetched {len(keywords)} keywords from AccuRanker.")

    previous_state = load_state()
    is_first_run = len(previous_state) == 0
    new_state = {}
    drops = []

    for kw in keywords:
        kw_id = str(kw["id"])
        current_rank = get_latest_rank(kw)
        currently_top3 = current_rank is not None and current_rank <= TOP_N

        previous = previous_state.get(kw_id)  # dict with "in_top3" and "rank", or None
        was_top3 = previous.get("in_top3") if previous else None
        previous_rank = previous.get("rank") if previous else None

        if was_top3 is True and currently_top3 is False:
            search_type_label = SEARCH_TYPE_LABELS.get(kw.get("search_type"), "Unknown")
            drops.append(
                {
                    "keyword": kw["keyword"],
                    "search_type": search_type_label,
                    "previous_rank": previous_rank,
                    "current_rank": current_rank,
                }
            )

        new_state[kw_id] = {"in_top3": currently_top3, "rank": current_rank}

    if is_first_run:
        print("First run: saving baseline, not sending any email yet.")
    elif drops:
        text_body = build_text_body(drops)
        html_body = build_html_body(drops)
        send_email(f"AccuRanker: {len(drops)} keyword(s) dropped out of top {TOP_N}", text_body, html_body)
        print(f"Sent alert email for {len(drops)} keyword(s).")
    else:
        print("No changes to report.")

    save_state(new_state)


if __name__ == "__main__":
    main()
