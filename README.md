# AccuRanker Alert Templates

Skabelon-repo til automatiske AccuRanker-alarmer via GitHub Actions. Hver
kunde bruger **"Use this template"** til at få sin egen kopi, med egne
secrets/nøgler - ingen kunde-data deles mellem repos.

Se **[SETUP.md](SETUP.md)** for selve opsætningsguiden.

## Struktur

```
common/
  accuranker_client.py   ← delt API-klient (autentificering, pagination)
  notify.py               ← delt mail-afsendelse (Resend eller SMTP, flere modtagere)
agents/
  preferred_url_check.py  ← tjekker om preferred URL stadig matcher
state/
  *.json                  ← gemt tilstand pr. agent, så vi kan opdage ÆNDRINGER
                             (ikke bare rapportere alt der er "forkert" hver dag)
.github/workflows/
  *.yml                   ← ét workflow pr. agent, egen tidsplan og on/off
```

## Nuværende agenter
| Agent | Trigger | Frekvens |
|---|---|---|
| `preferred_url_check.py` | Søgeord holdt op med at matche sin preferred landing page | Dagligt |

## Sådan tilføjes en ny agent
Alle agenter deler samme mønster, så en ny tager typisk kort tid at bygge:

1. Opret `agents/<navn>_check.py`, brug `preferred_url_check.py` som skabelon
2. Genbrug `common/accuranker_client.fetch_all_keywords(...)` til data
3. Genbrug `common/notify.send_email(...)` til alarmering
4. Gem egen tilstand i `state/<navn>_state.json`
5. Kopiér `.github/workflows/preferred-url-check.yml` til
   `.github/workflows/<navn>-check.yml`, og ret filnavnet i `run:`-linjen samt
   evt. tidsplanen

Planlagte/fremtidige agenter (ikke bygget endnu): rank-fald, share of
voice-fald, AI Overview-ændringer.
