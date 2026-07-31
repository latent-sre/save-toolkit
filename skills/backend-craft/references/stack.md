# Backend stack selection

Read this when starting a **greenfield** service. An existing repository's stack always wins —
if you are working in one, you do not need this file.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Framework & observability
- Python is primary → **FastAPI** (pydantic validation + async + OpenAPI for free); Flask is fine for
  small; Go → `net/http`/chi. Follow the repository's established language conventions for the implementation.
- Emit **RED metrics + structured logs + trace propagation**, including approved request/correlation
  fields, and expose distinct **health/readiness endpoints** for PCF. Deployment execution belongs to
  the human release owner after the target, action, health check, and rollback are approved.

## Auth & secrets (on PCF)
- Read credentials from the **bound service / `VCAP_SERVICES`** or env — **never hardcode**, never put a
  token in a flag, log line, error, or the SPA bundle. Load least-privilege scopes.
- **Refresh expiring tokens** (UAA/OAuth) ahead of expiry; handle a mid-run `401` by re-authing once.
- Request a `reviewer` security pass for anything touching auth or secrets.
