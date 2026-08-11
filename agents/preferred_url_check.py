"""
Agent: Preferred URL check.

Sends an alert if a keyword that PREVIOUSLY matched its "preferred landing
page" in AccuRanker no longer does. Only triggers on the transition itself
("matched -> no longer matches"), not for keywords that already didn't
match at the last run.

Required repository variables (Settings -> Secrets and variables -> Actions -> Variables):
  ACCURANKER_DOMAIN_ID   - the AccuRanker domain_id to monitor
  EMAIL_METHOD           - "resend" or "smtp"
  ALERT_EMAIL_FROM        - sender address

Required secrets (same place, under Secrets):
  ACCURANKER_API_KEY
  ALERT_EMAILS            - comma-separated list of recipients
  RESEND_API_KEY          - if EMAIL_METHOD=resend
  SMTP_HOST / SMTP_PORT / SMTP_USERNAME / SMTP_PASSWORD - if EMAIL_METHOD=smtp
"""

import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.accuranker_client import fetch_all_keywords  # noqa: E402
from common.notify import send_email  # noqa: E402

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state", "preferred_url_state.json")
FIELDS = "id,keyword,search_type,preferred_landing_page,ranks.landing_page,ranks.rank,ranks.created_at"

SEARCH_TYPE_LABELS = {1: "Desktop", 2: "Mobile"}

# Occasionally AccuRanker shows a temporary glitch where many keywords briefly
# report a very poor rank (or no rank at all) for a single day, then recover
# on their own. To avoid false alerts from this noise, a preferred URL
# mismatch is only considered "real" if the keyword is actually ranking, and
# ranking reasonably well (better than this threshold).
RANK_NOISE_THRESHOLD = 100


def get_latest_rank_info(keyword_obj):
    """Returns (landing_page_path, rank) from the most recent rank entry."""
    ranks = keyword_obj.get("ranks") or []
    if not ranks:
        return None, None
    latest = max(ranks, key=lambda r: r.get("created_at") or "")
    landing_page = latest.get("landing_page")
    path = landing_page.get("path") if landing_page else None
    rank = latest.get("rank")
    return path, rank


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


def build_text_body(regressions):
    """Plain text version (fallback for email clients without HTML rendering)."""
    lines = []
    for r in regressions:
        current = r["current"] or "(not ranking at all)"
        lines.append(
            f"{r['keyword']} ({r['search_type']})\n"
            f"  Preferred:             {r['preferred']}\n"
            f"  Currently ranking on: {current}\n"
        )
    return (
        f"{len(regressions)} keyword(s) have stopped matching their preferred URL:\n\n"
        + "\n".join(lines)
        + "\nCheck AccuRanker for details."
    )


def build_html_body(regressions):
    """HTML table with the keyword in bold, device (Desktop/Mobile), the
    preferred URL, and what is actually ranking now. Inline CSS, since most
    email clients ignore external stylesheets."""
    rows = []
    for r in regressions:
        current = r["current"] or "(not ranking at all)"
        rows.append(
            "<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'><strong>{r['keyword']}</strong></td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'>{r['search_type']}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'>{r['preferred']}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;color:#c0392b;'>{current}</td>"
            "</tr>"
        )

    return (
        "<div style='font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222;'>"
        f"<p>{len(regressions)} keyword(s) have stopped matching their preferred URL:</p>"
        "<table style='border-collapse:collapse;width:100%;'>"
        "<thead><tr>"
        "<th style='text-align:left;padding:8px 12px;border-bottom:2px solid #ccc;'>Keyword</th>"
        "<th style='text-align:left;padding:8px 12px;border-bottom:2px solid #ccc;'>Device</th>"
        "<th style='text-align:left;padding:8px 12px;border-bottom:2px solid #ccc;'>Preferred URL</th>"
        "<th style='text-align:left;padding:8px 12px;border-bottom:2px solid #ccc;'>Currently ranking on</th>"
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
    regressions = []

    for kw in keywords:
        kw_id = str(kw["id"])
        preferred = kw.get("preferred_landing_page")
        preferred_path = preferred.get("path") if preferred else None
        if preferred_path is None:
            continue  # no preferred URL set - not relevant to monitor

        current_path, current_rank = get_latest_rank_info(kw)
        currently_matches = current_path == preferred_path
        was_matching = previous_state.get(kw_id)

        if was_matching is True and currently_matches is False:
            is_meaningful = current_rank is not None and current_rank < RANK_NOISE_THRESHOLD
            if is_meaningful:
                search_type_label = SEARCH_TYPE_LABELS.get(kw.get("search_type"), "Unknown")
                regressions.append(
                    {
                        "keyword": kw["keyword"],
                        "search_type": search_type_label,
                        "preferred": preferred_path,
                        "current": current_path,
                    }
                )

        new_state[kw_id] = currently_matches

    if is_first_run:
        print("First run: saving baseline, not sending any email yet.")
    elif regressions:
        text_body = build_text_body(regressions)
        html_body = build_html_body(regressions)
        send_email(
            f"AccuRanker: {len(regressions)} preferred URL mismatch(es)",
            text_body,
            html_body,
        )
        print(f"Sent alert email for {len(regressions)} keyword(s).")
    else:
        print("No changes to report.")

    save_state(new_state)


if __name__ == "__main__":
    main()
