"""
Agent: Preferred URL-tjek.

Sender en alarm, hvis et søgeord, der FØR matchede sin "preferred landing
page" i AccuRanker, ikke længere gør det. Trigges kun på selve overgangen
("matchede -> matcher ikke længere"), ikke for søgeord der allerede ikke
matchede ved sidste kørsel.

Nødvendige repository variables (Settings -> Secrets and variables -> Actions -> Variables):
  ACCURANKER_DOMAIN_ID   - AccuRanker domain_id der skal overvåges
  EMAIL_METHOD           - "resend" eller "smtp"
  ALERT_EMAIL_FROM        - afsenderadresse

Nødvendige secrets (samme sted, under Secrets):
  ACCURANKER_API_KEY
  ALERT_EMAILS            - kommasepareret liste af modtagere
  RESEND_API_KEY          - hvis EMAIL_METHOD=resend
  SMTP_HOST / SMTP_PORT / SMTP_USERNAME / SMTP_PASSWORD - hvis EMAIL_METHOD=smtp
"""

import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.accuranker_client import fetch_all_keywords  # noqa: E402
from common.notify import send_email  # noqa: E402

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state", "preferred_url_state.json")
FIELDS = "id,keyword,search_type,preferred_landing_page,ranks.landing_page,ranks.created_at"

SEARCH_TYPE_LABELS = {1: "Desktop", 2: "Mobile"}


def get_latest_landing_page_path(keyword_obj):
    ranks = keyword_obj.get("ranks") or []
    if not ranks:
        return None
    latest = max(ranks, key=lambda r: r.get("created_at") or "")
    landing_page = latest.get("landing_page")
    return landing_page.get("path") if landing_page else None


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            print(f"ADVARSEL: {STATE_FILE} indeholdt ugyldig JSON - starter med tom tilstand.")
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
            f"  Preferred:      {r['preferred']}\n"
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
    print(f"Hentede {len(keywords)} søgeord fra AccuRanker.")

    previous_state = load_state()
    is_first_run = len(previous_state) == 0
    new_state = {}
    regressions = []

    for kw in keywords:
        kw_id = str(kw["id"])
        preferred = kw.get("preferred_landing_page")
        preferred_path = preferred.get("path") if preferred else None
        if preferred_path is None:
            continue  # intet preferred URL sat - ikke relevant at overvåge

        current_path = get_latest_landing_page_path(kw)
        currently_matches = current_path == preferred_path
        was_matching = previous_state.get(kw_id)

        if was_matching is True and currently_matches is False:
            search_type_label = SEARCH_TYPE_LABELS.get(kw.get("search_type"), "Ukendt")
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
        print("Første kørsel: gemmer baseline, sender ingen mail endnu.")
    elif regressions:
        text_body = build_text_body(regressions)
        html_body = build_html_body(regressions)
        send_email(
            f"AccuRanker: {len(regressions)} preferred URL mismatch(es)",
            text_body,
            html_body,
        )
        print(f"Sendte alarm-mail for {len(regressions)} søgeord.")
    else:
        print("Ingen ændringer at rapportere.")

    save_state(new_state)


if __name__ == "__main__":
    main()
