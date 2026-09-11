# Terms and roles

Defined once here; other skills use these words without restating them. A responder who meets one
of them in `production-change-gate`, `incident-investigation`, or an alert can read this file alone.

| Term or role | What it means on this team |
|---|---|
| Blast radius | The set of users, requests, services, or environments a change or failure can reach. State it as named targets and counts ("all `checkout` instances in prod", "one region"), never as an adjective. `production-change-gate` records it as required impact evidence after the tier is chosen from the action's reversibility and access-path effects; a small blast radius never lowers a tier. |
| Golden signals | Latency, traffic, errors, saturation (the Google SRE four). RED (rate, errors, duration) is the request-driven subset for a service; USE (utilization, saturation, errors) is the resource view for a host, pool, or queue. |
| Human release owner | The human assigned to execute a production change and own its rollback; named on the change record where the process requires one (the incident fast path defers that record without removing the role). Agents recommend; this person applies. *[unverified — the team has not recorded a default holder or rota here; record it when a human owner does]* |
| The platform team | The team that operates the PCF foundation itself (BOSH, Ops Manager, Diego cells, Gorouter, CredHub/UAA, upgrades) — see "The platform boundary" in the skill entrypoint. Symptoms on their side are escalated with evidence, not debugged. *[sourced: operator statement 2026-08-21]* |
| The human security incident owner | The person paged for a suspected compromise or abuse. No fleet agent owns security incident response; a reliability responder who suspects compromise escalates to this person and preserves evidence rather than restarting. *[unverified — no rota or title is recorded; record it here]* |
| Incident commander | The human coordinating the response and its authoritative record. They may explicitly invoke `incident-command` for advice; loading guidance never transfers this role. |
