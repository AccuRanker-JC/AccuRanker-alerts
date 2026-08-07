# AccuRanker Alert Templates

Template repository for automated AccuRanker alerts via GitHub Actions. Each
customer uses **"Use this template"** to get their own copy, with their own
secrets/keys — no customer data is shared between repos.

See **[SETUP.md](SETUP.md)** for the setup guide itself.

## Structure

```
common/
  accuranker_client.py   ← shared API client (authentication, pagination)
  notify.py               ← shared email sending (Resend or SMTP, multiple recipients)
agents/
  preferred_url_check.py  ← checks whether the preferred URL still matches
state/
  *.json                  ← saved state per agent, so we can detect CHANGES
                             (not just report everything that's "wrong" every day)
.github/workflows/
  *.yml                   ← one workflow per agent, own schedule and on/off switch
```

## Current agents
| Agent | Trigger | Frequency |
|---|---|---|
| `preferred_url_check.py` | A keyword stopped matching its preferred landing page | Daily |

## How to add a new agent
All agents share the same pattern, so a new one is typically quick to build:

1. Create `agents/<name>_check.py`, using `preferred_url_check.py` as a template
2. Reuse `common/accuranker_client.fetch_all_keywords(...)` for data
3. Reuse `common/notify.send_email(...)` for alerting
4. Store its own state in `state/<name>_state.json`
5. Copy `.github/workflows/preferred-url-check.yml` to
   `.github/workflows/<name>-check.yml`, and update the filename in the
   `run:` line as well as the schedule if needed

Planned/future agents (not built yet): rank drops, share of voice drops,
AI Overview changes.
