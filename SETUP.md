# Opsætning

Denne guide gælder for alle agenter i dette repo (fx `preferred_url_check.py`).
Følg den én gang - agenterne deler den samme opsætning.

## 1. Opret dit eget repo fra skabelonen
Klik **"Use this template"** på skabelon-repo'et → giv dit nye repo et navn →
**Create repository**. Du får nu en fuld kopi, uden git-historik fra
skabelonen, som du selv ejer og styrer.

## 2. Repository variables (ikke-følsomme indstillinger)
**Settings → Secrets and variables → Actions → fanen "Variables" → New
repository variable.**

| Navn | Værdi | Forklaring |
|---|---|---|
| `ACCURANKER_DOMAIN_ID` | fx `343517` | Find det i AccuRanker under domænets indstillinger, eller spørg din AccuRanker-kontakt |
| `EMAIL_METHOD` | `resend` eller `smtp` | Se afsnit 4 |
| `ALERT_EMAIL_FROM` | fx `alerts@dinvirksomhed.dk` | Afsenderadresse på alarmerne |

## 3. Secrets (følsomme nøgler)
**Samme sted, men fanen "Secrets".**

| Navn | Værdi |
|---|---|
| `ACCURANKER_API_KEY` | Din AccuRanker API-nøgle (Kontoindstillinger → API) |
| `ALERT_EMAILS` | Modtagere, kommasepareret: `person1@firma.dk,person2@firma.dk` |

Plus **enten** Resend- **eller** SMTP-secrets, afhængig af dit valg i punkt 4.

## 4. Vælg afsendelsesmetode

### Mulighed A: Resend (anbefalet til de fleste)
1. Opret konto på resend.com
2. **Vigtigt hvis du vil sende til mere end én modtager:** verificér dit eget
   domæne under Resend → Domains → Add Domain, og følg deres DNS-instruktioner.
   Uden det kan Resend kun sende til den mail, kontoen selv er oprettet med -
   det holder ikke i praksis, hvis I er flere stakeholders.
3. Opret en API-nøgle under Resend → API Keys
4. Secrets: `RESEND_API_KEY`
5. Sæt `ALERT_EMAIL_FROM` til en adresse på dit verificerede domæne, fx
   `alerts@dinvirksomhed.dk` (ikke `onboarding@resend.dev`, som kun er til
   hurtig test med én modtager)

### Mulighed B: SMTP (hvis I allerede har en mailserver)
Secrets: `SMTP_HOST`, `SMTP_PORT` (typisk 587), `SMTP_USERNAME`, `SMTP_PASSWORD`.

## 5. Test det
**Actions**-fanen → vælg workflowet → **Run workflow**. Første kørsel sender
ingen mail (den gemmer bare en baseline) - det er forventet. Kør den igen for
at bekræfte, at logikken virker som ventet, eller lav en midlertidig
testændring i AccuRanker for at trigge en reel alarm.

## 6. Løbende drift
Workflowet kører derefter automatisk på det skema, der står i selve
workflow-filen (`.github/workflows/*.yml`). Du kan altid pause en agent via
**Actions → vælg workflow → ••• → Disable workflow**, eller justere
tidspunktet ved at redigere `cron`-linjen.

## Fejlfinding
- **Ingen mail, selvom du forventede det:** tjek loggen for "Kør ...-tjek" i
  Actions - den fortæller om `state`-filen fandtes fra før (så det ikke er
  første kørsel).
- **Fejl fra Resend om afsender/modtager:** næsten altid domæneverificering,
  der mangler (se punkt 4A).
- **state-filen opdateres ikke:** tjek at `permissions: contents: write` står
  i workflow-filen (den følger med skabelonen, men kan være slettet ved en
  fejl).
