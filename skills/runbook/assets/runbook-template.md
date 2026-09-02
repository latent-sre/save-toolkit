---
schema_version: 1
runbook_id: <stable-runbook-slug>
service_id: <stable-service-slug>
status: draft | active | retired
alert_names: []
owner: <team/role>
severity: <P1|P2|P3|P4 / page | ticket>
source_revision: <repository@full-sha or reviewed release identifier>
last_reviewed: null
last_verified: null
verification_evidence: []
version: 1
---

# Runbook: <concise title / the alert this answers>

## Purpose & scope
What this runbook handles: <…>
**Out of scope** (do NOT use this for): <…>

## Trigger
The exact alert/symptom that brings you here: <alert name + condition, or observed symptom>
Dashboard: <link>  ·  Source/repo: <link>

## Prerequisites
- Access: <roles, Apps Manager org/space, VPN, tools>
- Tools: <Apps Manager, Splunk, Wavefront or PCF App Metrics; cf CLI v8 only if installed>
- Useful links: <dashboard, saved search, prior postmortem>

## Triage / first checks
1. Confirm impact (golden signals): <Apps Manager view, Splunk search, or Wavefront chart>
2. Decision tree:
   - If <condition A> → go to Procedure step <n>.
   - If <condition B> → this isn't the right runbook; see <other runbook> / escalate.

## Procedure
> Mark destructive steps ⚠️. Tier 2/3: record explicit human approval for the exact command/target plus rollback evidence before execution.

1. <imperative step>
   ```bash
   <command>
   ```
   Expected: <what you should see>
2. <next step> …

## Verification
How to confirm the issue is resolved: <command/dashboard + expected healthy state>

## Rollback / cleanup
How to undo each change above (reverse order): <exact steps>
Safe-abort: <how to stop mid-procedure without making it worse>

## Escalation
| When (condition / time elapsed) | Escalate to | How to reach |
|---|---|---|
| <e.g. not resolved in 15 min, or blast radius growing> | <role/team> | <pager / channel> |
| <platform-side signal: many apps / failing cells> | platform team | <…> |

Hand over: trigger, evidence, attempted steps, current state, and the current owner.

## Communication
- Notify: <channel / stakeholders> · Cadence while active: <the incident's agreed update interval>
- Initial / update / resolved message owner: <role>

## Post-Incident
- [ ] Append an Incident history row (below): version used, steps that held, steps that failed or
      were missing, follow-up id.
- [ ] Create a learning disposition for every missing, contradicted, or newly useful step.
- [ ] **Update this runbook** from supplied evidence when a disposition requires it.
- [ ] Change `last_verified` only when incoming rehearsal evidence binds this exact runbook version,
      target, actor, timestamp, and outcome; otherwise leave it unchanged (including `null`) and
      record the gap.
- [ ] File follow-up **automation candidates** (Crawl→Walk→Run) as tickets.
- [ ] If this was an incident, after recovery, hand the timeline and evidence to the `scribe` agent for retrospective documentation.

## Incident history (living-runbook accretion)
> Append one row per incident or rehearsal that used this runbook — newest first. Rows are evidence:
> never rewrite or delete them. A "failed / missing" cell that stays empty across many incidents is
> signal too. Three rows with the same manual fix ⇒ file the Crawl→Walk→Run automation candidate.

| Date (UTC) | Incident / drill ref | Version used | Steps that held | Steps that failed / were missing | Follow-up (disposition / PR or evidence reference) |
|---|---|---|---|---|---|
| <YYYY-MM-DD> | <postmortem or drill link> | <n> | <e.g. steps 1–3> | <e.g. step 4 output differed; no rollback for step 5> | <PR, evidence link, prepared, or proposed> |

## References
- Related runbooks: <…>
- Postmortems: <…>
- Alert definition / SLO: <…>
- Service card / alert card / knowledge index: <…>
- Provenance: <PR, target revision, and evidence references>
