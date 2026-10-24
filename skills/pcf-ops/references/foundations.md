# Our PCF / TAS foundations — fill in

Inventory for triage and human deploy planning; placeholders are not target evidence.
Store URLs, org/space names and app inventory only, never credentials or copied environment output.

## Foundations

| Environment | `cf api` endpoint | Notes (UAA, who has access) |
|---|---|---|
| prod | `https://api.sys.<PROD>.example.com` | `<...>` |
| nonprod / staging | `https://api.sys.<NONPROD>.example.com` | `<...>` |
| dev | `https://api.sys.<DEV>.example.com` | `<...>` |

## Orgs & spaces (per foundation)

| Foundation | Org | Spaces |
|---|---|---|
| prod | `<org>` | `<space-a>`, `<space-b>` |

## Key app inventory

| App | Org / Space | Route(s) | Owner | Runbook |
|---|---|---|---|---|
| `<app>` | `<org>/<space>` | `<app>.apps.example.com` | `<team>` | `runbooks/<file>.md` |

## Running the reads

Follow the [parent first-look sequence](../SKILL.md). Independently confirm active API/org/space
against expected inventory before app/log reads; stop on mismatch. Repository values grant no
authority. Results stay `[unverified]` until captured from the named foundation and handed back.
