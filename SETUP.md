# Setup

This guide applies to all agents in this repo (e.g. `preferred_url_check.py`).
Follow it once — the agents share the same setup.

## 1. Create your own repo from the template
Click **"Use this template"** on the template repo → give your new repo a
name → **Create repository**. You now get a full copy, without the
template's git history, which you own and control yourself.

## 2. Repository variables (non-sensitive settings)
**Settings → Secrets and variables → Actions → "Variables" tab → New
repository variable.**

| Name | Value | Explanation |
|---|---|---|
| `ACCURANKER_DOMAIN_ID` | e.g. `343517` or `343517,534653` | One domain, or several comma-separated domain IDs to monitor with a single agent. Find them in AccuRanker under each domain's settings |
| `EMAIL_METHOD` | `resend` or `smtp` | See section 4 |
| `ALERT_EMAIL_FROM` | e.g. `alerts@yourcompany.com` | Sender address for the alerts |

## 3. Secrets (sensitive keys)
**Same place, but the "Secrets" tab.**

| Name | Value |
|---|---|
| `ACCURANKER_API_KEY` | Your AccuRanker API key (Account settings → API) |

Plus **one recipient secret per agent** — this lets each check send to
different stakeholders if needed, without touching any code:

| Name | Value |
|---|---|
| `ALERT_EMAILS_PREFERRED_URL` | Recipients for the preferred URL check, comma-separated |
| `ALERT_EMAILS_TOP3_RANK` | Recipients for the top 3 rank drop check |
| `ALERT_EMAILS_ADS_TOP` | Recipients for the rank 1 + top ad check |

If you want the same people to receive everything, just use the same list
of addresses in all three secrets — it's still one secret per agent, just
with identical values.

Plus **either** Resend **or** SMTP secrets, depending on your choice in
section 4.

## 4. Choose a sending method

### Option A: Resend (recommended for most)
1. Create an account at resend.com
2. **Important if you want to send to more than one recipient:** verify your
   own domain under Resend → Domains → Add Domain, and follow their DNS
   instructions. Without this, Resend can only send to the email the account
   itself was created with — that doesn't work in practice if you have
   multiple stakeholders.
3. Create an API key under Resend → API Keys
4. Secrets: `RESEND_API_KEY`
5. Set `ALERT_EMAIL_FROM` to an address on your verified domain, e.g.
   `alerts@yourcompany.com` (not `onboarding@resend.dev`, which is only for
   quick testing with a single recipient)

### Option B: SMTP (if you already have a mail server)
Secrets: `SMTP_HOST`, `SMTP_PORT` (typically 587), `SMTP_USERNAME`,
`SMTP_PASSWORD`.

## 5. Test it
**Actions** tab → select the workflow → **Run workflow**. The first run
sends no email (it just saves a baseline) — that's expected. Run it again
to confirm the logic works as intended, or make a temporary test change in
AccuRanker to trigger a real alert.

## 6. Ongoing operation
The workflow then runs automatically on the schedule set in the workflow
file itself (`.github/workflows/*.yml`). You can always pause an agent via
**Actions → select workflow → ••• → Disable workflow**, or adjust the
timing by editing the `cron` line.

## Troubleshooting
- **No email, even though you expected one:** check the log for "Run
  ...-check" in Actions — it will tell you whether the `state` file already
  existed (so it's not the first run).
- **Error from Resend about sender/recipient:** almost always missing
  domain verification (see section 4A).
- **State file isn't updating:** check that `permissions: contents: write`
  is present in the workflow file (it ships with the template, but could be
  removed by mistake).
