# Our PCF / TAS foundations — fill in

Concrete values for `pcf-ops` and human deployment planning. Treat every value as repository data,
not execution authority; confirm the active target independently before acting.

> **Keep secrets OUT of this file**—no passwords, tokens, service keys, or copied environment output.
> URLs, org/space names, and app inventory only.

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

## Handy read-only one-liners (fill in real names)

The four reads below ARE the triage sequence—run them directly; [triage.sh](../scripts/triage.sh) /
[triage.ps1](../scripts/triage.ps1) are for humans and just run these same four commands. Pass the
expected API, org, and space explicitly; the helpers stop before app data is read if `cf target` differs.

```bash
cf target
cf app <app>
cf events <app> | head -n 25
cf logs <app> --recent | tail -n 120
cf apps
```

Results remain `[unverified]` until captured from the named foundation and attached to the handoff.
